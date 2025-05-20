from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
import chromadb
from chromadb.utils import embedding_functions
from groq import Groq
from datetime import datetime
import os



def retrieve_data(query):
    """
    Retrieves top matching recipes from ChromaDB and returns both titles and documents.
    """
    chroma_client = chromadb.HttpClient(host='localhost', port=8000)

    model_name = "akhooli/Arabic-SBERT-100K"
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)

    try:
        collection = chroma_client.get_collection("recipestest", embedding_function=sentence_transformer_ef)
        print("Collection 'recipestest' found.")
    except chromadb.errors.InvalidCollectionException:
        print("Collection 'recipestest' does not exist. Please add data first.")
        return []

    results = collection.query(
        query_texts=[query],
        n_results=5,
        include=["documents", "metadatas"]  # Correct: include metadatas, not ids.
    )

    print("🔍 Raw ChromaDB Results:", results)

    structured_results = []
    for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
        structured_results.append({
            "title": metadata.get("title", "وصفة بدون عنوان"),
            "document": doc
        })


    return structured_results



def enhance_query_with_groq(query, chat_context=""):
    """
    This function uses the Groq API to enhance the query and determine if it's food-related.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    system_prompt = """
أنت مراقب لتحليل المحادثة بين المستخدم والروبوت، وهدفك هو تصنيف كل موقف بدقة لتحديد ما إذا كان يجب تنفيذ استرجاع لوصفة طعام.

 يجب تصنيف الحالة إلى واحدة فقط من الفئات الأربع التالية:

1. not food related  
2. respond based on chat history  
3. food generalized  
4. [اسم الأكلة أو نوع الطعام]

---

 1. not food related  
استخدم هذا التصنيف عندما يكون الحديث:
- اجتماعي أو تعارف فقط
- أو تعبير عن الجوع أو الرغبة العامة بالأكل بدون نية الطلب
- أو يحتوي على ذكر طعام فقط كمعلومة شخصية أو رأي بدون نية استرجاع
- أو عندما لا يوجد أي إشارة واضحة إلى نية الحصول على وصفة

 مهم: حتى لو ذَكر المستخدم اسم أكلة، لا تخرجها إن لم يكن هناك طلب صريح أو موافقة واضحة.

**أمثلة:**
- "أنا جعان"
- "كنت بفكر في الأكل"
- "بحب شوربة عدس"
- "الأكل المصري مميز"
- "الأكلة دي ذكرتني بأيام زمان"
- "أنا بحب الأكل النباتي"
- "زمان كنت باكل كشري كل أسبوع"
- "أنا شبعان بس بحب الملوخية"
- "تحب نحكي عن أكلات من زمان؟"
- "الأكل عمومًا لذيذ"

---

 2. respond based on chat history  
استخدم هذا التصنيف إذا كان حديث المستخدم تعليقًا أو متابعة لوصفة تم عرضها مسبقًا في نفس الجلسة، مثل تجربة، تأكيد، أو موافقة متأخرة.

**أمثلة:**
- "جربتها وكانت ممتازة"
- "آه فعلاً طلعت حلوة"
- "اللي فاتت كانت لذيذة"
- "نرجع للوصفة اللي فاتت"
- "ماشي نعمل اللي فاتت تاني"
- "عجبتني الوصفة اللي فاتت"
- "لا انا عايز الوصفه دى و ممكن نشيل منها البصل"

تأكد من التركيز فى هذه الحاله على السياق السابق، ولا تخرج أي أكلة جديدة أو اقتراحات حيث ان المستخدم يتحدث عن وصفة تم استرجاعها بالفعل.

---

 3. food generalized  
استخدم هذا التصنيف عندما يتحدث المستخدم عن نوع طعام عام بدون تحديد اسم أكلة، مع وضوح نيته في الأكل أو الحصول على اقتراح، ولكن دون ذكر أكلة محددة بعد.

**أمثلة:**
- "أنا عايز شوربة"
- "نفسي في حاجة نباتية"
- "أنا بفكر في أكل بحري"
- "حابب حاجة خفيفة"
- "أنا حابب أكلة في الفرن"
- "ممكن نعمل حاجة مشوية؟"
- "أنا مايل للمعجنات"
- "أنا عايز حاجة سخنة"
- "ممكن أكل على السريع؟"
- "حابب أبدأ بحاجة خفيفة"
- "أنا بفكر في صنف خفيف مش تقيل"

 ملاحظة: في هذه الحالات، لا يتم تنفيذ استخراج اسم اكله بعد — بل يُترك القرار للروبوت ليقود الحوار نحو تحديد أكلة واضحة.

---

 4. [اسم الأكلة أو نوع الطعام]
استخدم هذا التصنيف فقط عندما:
- يطلب المستخدم صراحة أكلة أو وصفة محددة
- أو يوافق بوضوح على اقتراح معين تم تقديمه في الرسالة السابقة من الروبوت (ولم يتم عرضه بعد)

 في هذه الحالة، يجب أن تستخرج اسم الأكلة من رسالة المستخدم أو من الاقتراح السابق من الروبوت.

 لا تستخدم هذا التصنيف إذا لم تكن هناك نية واضحة لطلب الوصفة أو موافقة مباشرة على اقتراح.

**ممنوع منعًا باتًا:**
ان تخلط بين هذه الحاله و حالة ان المستخدم يتحدث عب وصفة تم استرجاعها بالفعل.

استخراج اسم وصفه يجب ان يكون مبنى على قرار اكيد ان المستخدم يريد وصفه جديده.
اذا كان هناك شك فى ذلك، لا تخرج اسم اكلة ابدا!

**أمثلة:**
- "هاتلي وصفة شوربة عدس" ⟶ شوربة عدس  
- "أنا عايز كشري" ⟶ كشري  
- "جربلي المسقعة" ⟶ مسقعة  
- "ممكن وصفة طاجن بامية؟" ⟶ طاجن بامية  
- "نفسي في أكلة فيها جمبري" ⟶ أكلة فيها جمبري  
- الروبوت: "تحب شوربة الطماطم؟"  
  المستخدم: "آه جربها" ⟶ شوربة الطماطم  
- الروبوت: "ممكن نعمل كبسة؟"  
  المستخدم: "ماشي" ⟶ كبسة  
- الروبوت: "تحب أعملك شيش طاووق؟"  
  المستخدم: "أيوه جرب" ⟶ شيش طاووق  

---

 تعليمات إضافية للتعامل مع الحالات الخاصة:

- إذا احتوت الرسالة على نوع طعام عام وأكلة محددة، يتم اختيار حالة [اسم الأكلة] فقط إن وُجدت نية واضحة للطلب أو الموافقة.
- العبارات مثل "ليه لأ"، "ماشي جربها"، "تمام امشي عليها" تُعتبر موافقة صريحة إذا جاءت مباشرة بعد اقتراح من الروبوت.
- إذا رفض المستخدم الاقتراح (مثل: "مش عايز كبسة") لا يتم تنفيذ الاسترجاع لهذا الاقتراح.
- إذا وافق المستخدم على اقتراح غير محدد (مثل: "ممكن نعمل أكلة؟" ← "ماشي") فهذا لا يُعتبر موافقة على نوع طعام معين.
- اذا احتوت الرساله على طلب فطار او غدا او عشاء، لا تخرج اسم أكله محدده, بل استخدم food generalized.

---

 ممنوع منعًا باتًا:
- لا تخرج اسم أكلة إلا إذا وُجد طلب صريح أو موافقة صريحة على اقتراح محدد.
- لا تخترع أكلة أو تفترض نية غير مذكورة.
- لا تكمّل، لا تشرح، لا تفسّر.
- لا تتفاعل — فقط صنّف بدقة و ذكاء عالى.

---

 المخرجات المقبولة فقط:

- not food related  
- respond based on chat history  
- food generalized  
- [اسم أكلة أو نوع طعام حقيقي مذكور بوضوح فقط]
بدون اي زخارف، علامات ترقيم، أو تنسيق خاص او شرح او اسباب او تعليلات 

"""

    full_input = f"""سياق المحادثة السابق:
        {chat_context}

        رسالة المستخدم الحالية:
        {query}
        """
    print("Full Input to query enhancer/classifier:", full_input)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_input},
    ]

    chat_completion = client.chat.completions.create(
        messages=messages,
        model="meta-llama/llama-4-maverick-17b-128e-instruct",  # Change to appropriate model for query enhancement
        temperature=0.0,
    )

    return chat_completion.choices[0].message.content



def choose_from_suggestions(suggestions_string: str) -> str:
    """
    Displays a list of Arabic food suggestions, prompts the user to choose one, and returns the selected option.
    """
    suggestions = [line.strip() for line in suggestions_string.strip().split('\n') if line.strip()]
    
    print("Please choose one of the following options:")
    for idx, suggestion in enumerate(suggestions, 1):
        print(f"{idx}. {suggestion}")
    
    selected_index = None
    while selected_index is None:
        try:
            choice = int(input("Enter the number of your choice: "))
            if 1 <= choice <= len(suggestions):
                selected_index = choice - 1
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
    
    return suggestions[selected_index]

def select_suggestion_from_list(suggestions_string: str) -> list:
    """
    Takes a string of newline-separated suggestions and returns them as a list (without printing or prompting).
    """
    return [line.strip() for line in suggestions_string.strip().split('\n') if line.strip()]


class WebSocketBotSession:
    def __init__(self):
        self.memory = ConversationBufferWindowMemory(k=12, memory_key="chat_history", return_messages=True)
        self.expecting_choice = False
        self.suggestions = []
        self.original_question = ""
        self.user_name = None
        self.user_gender = None
        self.user_profession = None 
        self.mode = None
        self.retrieved_documents = {}  # Holds full recipes keyed by title
        self.last_user_query = None
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.model = 'meta-llama/llama-4-maverick-17b-128e-instruct'
        self.groq_chat = ChatGroq(groq_api_key=self.groq_api_key, model_name=self.model)

    def set_user_info(self, name: str, gender: str, profession: str = None, likes: list = None, dislikes: list = None, allergies: list = None, favorite_recipes: list = None):
        self.user_name = name
        self.user_gender = gender
        self.user_profession = profession
        self.user_likes = likes or []
        self.user_dislikes = dislikes or []
        self.user_allergies = allergies or []
        self.user_favorite_recipes = favorite_recipes or []
        self._update_system_prompt()

    def set_mode(self, mode):
        self.mode = mode
        self._update_system_prompt()


    def get_recent_chat_context(self, n=10):
        history = self.memory.load_memory_variables({})["chat_history"]
        return "\n".join(
            f"{m.type}: {m.content}" for m in history[-n:]
        )

    def _update_system_prompt(self):
    
        if self.user_profession:
            profession = self.user_profession.strip().lower()
            if "مهندس" in profession:
                title = "بشمهندس" if self.user_gender == "male" else "بشمهندسه"
            elif "دكتور" in profession:
                title = "دكتور" if self.user_gender == "male" else "دكتوره"
            else:
                title = self.user_profession
        else:
            title = "أستاذ" if self.user_gender == "male" else "أستاذة"
        
        likes_str = "، ".join(self.user_likes) if self.user_likes else "لا يوجد"
        dislikes_str = "، ".join(self.user_dislikes) if self.user_dislikes else "لا يوجد"
        allergies_str = "، ".join(self.user_allergies) if self.user_allergies else "لا يوجد"
        favorites_titles = [fav["title"] for fav in self.user_favorite_recipes] if self.user_favorite_recipes else []
        favorites_str = "، ".join(favorites_titles) if favorites_titles else "لا يوجد"
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")

        core_prompt = f"""

        أنت روبوت دردشة ذكي وودود ولديك حس فكاهي خفيف، وتهتم فقط بالطعام. تتحدث بالكامل باللغة العربية، وبالتحديد باللهجة المصرية.
المستخدم الذي تتحدث معه هو: {title} {self.user_name}.
يجب أن تناديه بشكل طبيعي بلقبه أو باسمه في بداية المحادثة أو في لحظات مناسبة فقط، دون الإكثار أو التكرار غير الطبيعي.
المستخدم {self.user_gender}.
حافظ دائما على مخاطبة المستخدم حسب هو ذكر ام انثى.
هذا هو ملخص معلومات المستخدم:
  "الأكلات المفضلة": {likes_str}
  "الأكلات غير المفضلة": {dislikes_str}
  "الحساسيات الغذائية": {allergies_str}
  "الوصفات المفضله لدى المستخدم فى المحادثات السابقة": {favorites_str}
يجب أن تأخذ هذه المعلومات في الاعتبار عند اقتراح الوصفات أو الأكلات و عند التفاعل مع المستخدم و يجب ان يكون استخدامهم منطقى.
.يجب التشديد على الحساسيات الغذائية، حيث يجب تجنب او عرض بدائل أي مكونات أو أكلات تحتوي على مكونات تسبب حساسية للمستخدم 

المحادثة الان هي: {self.mode}
اذا كانت المحادثة voice :
 تعليمات خاصة بنمط المحادثة الصوتية:

- يجب أن تكون جميع الردود **موجزة وواضحة ومباشرة**.
- لا تطرح أكثر من سؤال في نفس الرسالة.
- استخدم **اللغة العربية بالتشكيل الكامل** لتسهيل النطق عبر نموذج تحويل النص إلى كلام.
- إذا تم استرجاع وصفة، **لا تُعرض الوصفة كاملة**، بل قدم **ملخصًا بسيطًا جدًا** عنها في سطر أو سطرين فقط يوضح اسم الأكلة وطريقة التحضير العامة.
- تَجنّب التفاصيل الطويلة أو القوائم أو الخطوات الكثيرة في الردود.

هدفك في هذا النمط هو أن تكون الردود مناسبة للاستماع السريع، دون تشويش أو تعقيد، وبطريقة تسهّل قراءتها صوتيًا للمستخدم.


معلومة عن الألقاب:
إذا كان المستخدم مهندسًا (مثال: مهندس أو مهندسة)، من الشائع في اللهجة المصرية مناداته بـ "بشمهندس" أو "يا هندسة" بطريقة ودودة. 
يمكنك استخدام "بشمهندس {self.user_name}" أو فقط "يا هندسة" في بداية الحديث أو عند التعليق، ولكن لا تفرط في الاستخدام.
نفس القاعدة تنطبق على الأطباء ("دكتور" أو "يا دكتور").

ممنوع منعا باتا الاختلاط فى لقب او نوع المستخدم.
استخدم الاكلات المفضله لدى المستخدم فى اقراحاتك و لكن لا تستخدمهم تحديدا و استخدم النوعية او الاكلات المشابهة بشكل عام.


يجب أن تستفيد من الوقت الحالي في المحادثة عند تقديم المقترحات، و تذكر أن الوقت الحالي هو: {current_time}، و التاريخ هو: {current_date}.
استخدام الوقت الحالى سيساعدك في تقديم اقتراحات ملائمة للمستخدم، مثل اقتراح وجبات خفيفة أو أكلات سريعة أو الإفطار أو الغداء أو العشاء، حسب الوقت الحالي.

تعليمات خاصة لكبار السن:
- تحدث بنبرة هادئة ومحترمة دائمًا.
- لا تستخدم لغة تقنية أو مصطلحات معقدة.
- اجعل الردود قصيرة ومباشرة وسهلة الفهم.
- إذا شعرت أن المستخدم أكبر سنًا، كن صبورًا وأعد التوضيح عند الحاجة.

عن نبرة الصوت:
- إذا كانت النبرة ودودة، تجاوب بحماس ودفء.
- إذا كانت النبرة غاضبة أو منزعجة، لا تعتذر فورًا، بل حاول تحويل الانفعال إلى مزاح خفيف محترم.
  مثل: "شكل حضرتك زعلان، بس أراهن إن الوصفة دي هتصلّح المزاج!"
  أو: "طب اديني فرصة أثبتلك إن الموضوع يستاهل... لو مطلعتش لذيذة، حقك عليّا!"

عن الشخصية:
- إذا كان المستخدم حازمًا، كن مباشرًا وفعالًا.
- إذا كان المستخدم مترددًا، اقترح بلطف وادعمه في اتخاذ القرار.
- إذا كان المستخدم يحب المزاح، رد عليه بخفة دم، دون مبالغة أو تهريج.

ممنوع تمامًا:
- لا تخترع وصفات أو تتحدث عن وصفات غير موجودة.
- لا تفترض وجود صنف إذا لم يتم استرجاعه من قاعدة البيانات.
- لا تقدم اقتراحات عامة عن الطعام إذا لم يتم طلبها بوضوح.
-
يُمنع منعًا باتًا ذكر أسماء وصفات دقيقة أو محددة مثل كشري بالعدس أو بيتزا مارجريتا أو لازانيا السبانخ أو أي وصفة بعينها. يجب أن تقتصر الاقتراحات فقط على أنواع عامة من الأطعمة أو مكوناتها مثل دجاج، لحم، مكرونة، أرز، شوربة، سلطات، مأكولات بحرية، خضروات، معجنات، حلويات، مشروبات، عصائر، أو غيرها. عليك أن تكون مبدعًا في اقتراح أنواع طعام عامة تناسب سياق المحادثة بدون التقيد بالأمثلة المذكورة هنا، ولكن تحت أي ظرف، لا تذكر وصفة كاملة أو اسم أكلة محددة. يجب أن تبقى الاقتراحات عامة وشاملة لضمان التوافق مع قاعدة البيانات وعدم افتراض وجود وصفة معينة بالاسم. إذا شعرت أن المستخدم يحتاج إلى اقتراح، استخدم مصطلحات عامة جدًا للطعام، مع الحفاظ على أسلوب طبيعي ومرن يناسب سير المحادثة.
إذا لم تتطابق الوصفات المسترجعة مع نية المستخدم، أخبره بلطافة:
- مثلًا: "النوع ده مش موجود حاليًا، ممكن توضح أكتر تحب تاكل إيه؟"
- ثم وجّه الحديث بشكل طبيعي حتى يعبر المستخدم عن طلب واضح لوصفة أو نوع أكل.

هدفك الأساسي:
أن يعبر المستخدم بوضوح عن وصفة أو نوع أكل يريده، لتقوم المنظومة بجلب الوصفة الدقيقة له من قاعدة البيانات.

مهامك:
- ابدأ الحديث بلقب المستخدم بشكل طبيعي (في أول سطر فقط أو عند الحاجة).
- إذا قال المستخدم شيئًا مثل "إزيك" أو "مساء الخير"، رد عليه بلطافة بدون الحديث عن الأكل.
- لا تقترح وصفات بنفسك. انتظر معزز الاستعلام ليحدد نية المستخدم.
- إذا تم استرجاع وصفة، اعرضها فورا كما هي دون تعديل أو تلخيص و يجب عليك عرضها كاملة.
- اعرض الوصفه المسترجعه كما هى بالتشكيل.
- احرص على مخاطبة المستخدم حسب نوعه (ذكر ام انثى) فى تعليمات الوصفه

إرشادات السلوك:
- لا تكرر اسم المستخدم أو لقبه كثيرًا هذا امر هام جدا
- استخدم الألقاب المناسبة فقط عند الحاجة (بشمهندس، يا دكتور، يا استاذ...).
- لا تكرر نفسك أو تتحدث بأسلوب روبوتي.
- إذا لم يفهم المستخدم أو كان غامضًا، وجّهه بلطافة لسؤاله عن الأكل.

تسلسل النظام:
1. حيّي المستخدم باسمه أو لقبه بطريقة طبيعية.
2. لا تقترح طعامًا إلا إذا طلب المستخدم وصفة أو نوع أكل بوضوح.
3. إذا ظهرت اقتراحات، انتظر اختيار المستخدم.
4. عندما تُسترجع وصفة، اعرضها كما هي دون تعديل.
5. إذا لم توجد وصفة مناسبة، اطلب من المستخدم توضيح رغبته.
6. استمر في الحديث بنبرة طبيعية، خفيفة، وودية.

ملحوظه هامه جدا جدا
- اعرض الوصفه المسترجعه كما هى بالتشكيل.
- تعامل مع المستخم حسب نوعه (ذكر ام انثى) فى تعليمات الوصفه
- اذا كانت الوصفة المسترجعه مكتوبه بصيغة المؤنث يجب تعديلها لتناسب المستخدم الذكر.
- اذا كانت المحادثة voice يجب ان تكون الوصفة مختصرة جدا و كل.
إذا كانت المحادثة صوتية (voice mode)، يجب أن تكون جميع الردود باللهجة المصرية، مكتوبة بالعربية مع التشكيل الكامل بطريقة تُساعِد على النُطق الصّحيح.

 استخدم التشكيل لتوضيح النُطق، حتى وإن لم يكن التشكيل فُصحى رسمي.
 التزم بالتشكيل في كل الكلمات، كما تُقال باللهجة المصرية.
 لا تَكتب الردود بدون تشكيل أبدًا في هذا النمط.

مثال: "إزَّاي أَقدَر أَساعِدَك؟" أو "طَب خُد الوَصفَة دي!"
- يجب ان يكون استخدام الاكلات المفضله لدى المستخدم منطقى و ليس بشكل عشوائى و يكون استخدامهم بشكل عام و ليس بشكل محدد.
- لا تخلط ابدا بين المحادثة ال voice و المحادثة ال text.
- لا تخلط ابدا فى الالقاب و لا نوع المستخدم.

كن عفويًا، صادقًا، ومتعاونًا، والهدف دائمًا أن تساعد المستخدم في اختيار وصفة حقيقية من قاعدة البيانات.
"""


        self.system_prompt = core_prompt.strip()

    async def handle_message(self, user_input: str):
        print(f"\n🟡 Received user message: {user_input}")
        self.original_question = user_input

        recent_context = self.get_recent_chat_context(n=10)
        query_result = enhance_query_with_groq(user_input, chat_context=recent_context)

        print(f"🧠 Query Enhancer Output:\n{query_result}\n")

        if query_result in ["not food related", "respond based on chat history","food generalized"]:
            print("🔍 Passing message directly to LLM without retrieval.\n")
            return await self._generate_response(user_input, query_result)

        documents = retrieve_data(query_result)
        if not documents:
            print("⚠️ No documents found. Responding with fallback.")
            return await self._generate_response(user_input, "لم أتمكن من العثور على وصفات مناسبة.")

        self.suggestions = [doc["title"] for doc in documents] + ["❌ لا أريد أي من هذه الخيارات"]  # Use titles as suggestions
        self.retrieved_documents = {doc["title"]: doc["document"] for doc in documents}
        self.expecting_choice = True

        print("📋 Recipe Titles Found:")
        for i, title in enumerate(self.suggestions, 1):
            print(f"{i}. {title}")

        return {
            "type": "suggestions",
            "message": "اختر رقم من الاختيارات التالية:",
            "suggestions": self.suggestions
        }

    async def handle_choice(self, choice_index: int):
        print(f"🟠 User selected choice index: {choice_index}")
        # Check if user chose to skip suggestions
        if choice_index == len(self.suggestions) - 1:
            print("🚫 User rejected all suggestions.")
            self.expecting_choice = False
            self.suggestions = []
            return await self._generate_response(self.original_question, "لم يتم اختيار أي وصفة. يمكنك التحدث بحرية الآن.")

        if 0 <= choice_index < len(self.suggestions):
            selected_title = self.suggestions[choice_index]
            print(f"✅ Selected Recipe Title: {selected_title}")

            retrieved_data = self.retrieved_documents[selected_title]
            print(f"📦 Retrieved Full Recipe:\n{retrieved_data}\n")

            self.expecting_choice = False
            self.suggestions = []  # 🛠️ ADD THIS to clear suggestions safely

            response = await self._generate_response(self.original_question, retrieved_data)
            response["selected_title"] = selected_title  # ✅ Good
            response["full_recipe"] = retrieved_data     # 🛠️ ADD THIS line to send the full recipe text

            return response

        else:
            print("❌ Invalid choice index received.")
            return {
                "type": "error",
                "message": "اختيار غير صالح. حاول رقم تاني."
            }

    
    async def _generate_response(self, user_input: str, retrieved_data: str):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{human_input}"),
        ])

        chat_history = self.memory.load_memory_variables({})["chat_history"]
        print(f"📚 Chat History Size: {len(chat_history)}")

        full_prompt = prompt.format_messages(
            chat_history=chat_history,
            human_input=user_input
        )

        print("🧠 Prompt Sent to LLM:")
        print(full_prompt)

        conversation_input = f"Retrieved Data: {retrieved_data}\nUser Question: {user_input}"

        conversation = LLMChain(
            llm=self.groq_chat,
            prompt=prompt,
            verbose=False,
            memory=self.memory,
        )

        response = conversation.predict(human_input=conversation_input)

        print("💬 Chatbot Response:\n", response)
        return {
            "type": "response",
            "message": response
        }

