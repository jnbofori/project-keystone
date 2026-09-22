## Step 1 - Install packages

import warnings
warnings.filterwarnings('ignore')
!pip install -q langchain langchain_community langchain_text_splitters sentence_transformers chromadb langchain_HuggingFace
!pip install -q langchain-core
!pip install langchain-groq
print("installation complete")

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import HuggingFaceHub
from langchain_core.documents import Document

print(f"Import complete")

## Step 3 - Documents

"""
═══════════════════════════════════════════════════════════════
SAMPLE DOCUMENTS (EXPANDED VERSION)
Longer content to demonstrate chunking
═══════════════════════════════════════════════════════════════
"""

documents = [
    """
    Company Policy: Remote Work Guidelines and Procedures

    Overview:
    Our company recognizes the importance of work-life balance and the benefits of flexible work arrangements. This policy outlines the guidelines and procedures for remote work opportunities available to eligible employees across all departments and locations.

    Eligibility Requirements:
    Full-time employees who have completed their probationary period (90 days) are eligible to apply for remote work arrangements. Part-time employees working 20+ hours per week may also be considered on a case-by-case basis. Eligibility depends on job responsibilities, performance history, and department needs. Managers have discretion to approve or deny requests based on business requirements.

    Remote Work Schedule:
    Employees can work remotely up to 3 days per week, with a minimum of 2 days in the office for team collaboration and meetings. Remote work requests must be submitted at least one week in advance and approved by direct managers through the HR portal. The schedule should be consistent from week to week to maintain team coordination, though flexibility is allowed for special circumstances with advance notice.

    Core Hours and Availability:
    Remote employees must be available and responsive during core business hours, which are 10:00 AM to 3:00 PM Eastern Standard Time for all US-based employees. International employees should coordinate with their managers to establish appropriate core hours based on time zones. During these hours, employees are expected to respond to emails within 30 minutes and be available for video calls. Lunch breaks should be communicated to team members via calendar blocks.

    Communication Requirements:
    Remote employees must maintain regular communication with their teams via our company Slack workspace. Daily check-ins with your immediate team are required at the start of each workday. All meetings should be scheduled with video conferencing links to accommodate remote participants. Status updates on ongoing projects should be posted in designated Slack channels at least twice daily. Emergency contact information must be kept current in the HR system.

    Equipment and Technology:
    The IT department provides necessary equipment for home office setups, including laptops, monitors, keyboards, mice, and headsets. Equipment requests must be submitted through the IT portal with manager approval. Employees are responsible for maintaining a secure internet connection with minimum speeds of 25 Mbps download and 5 Mbps upload. The company provides a monthly internet stipend of $50 to offset connectivity costs. All company equipment must be returned upon termination or if remote work privileges are revoked.

    Home Office Requirements:
    Remote employees must maintain a dedicated workspace that is quiet, private, and conducive to professional work. The workspace should have adequate lighting and ergonomic furniture to prevent workplace injuries. Video call backgrounds should be professional and free from distractions. Family members or roommates should be informed of work hours to minimize interruptions during meetings and calls.

    Security and Confidentiality:
    Remote employees are responsible for maintaining the security and confidentiality of company information. All company data must be stored on company servers or approved cloud services - never on personal devices or drives. VPN access is required for all remote connections to company resources. Employees should lock their computers when stepping away and ensure that confidential information is not visible to others in shared spaces. Any security incidents must be reported immediately to the IT security team.

    Performance Expectations:
    Remote work is a privilege that can be revoked if performance standards are not met. Employees working remotely are held to the same productivity and quality standards as in-office workers. Managers will conduct regular check-ins to assess performance and address any concerns. Failure to meet deadlines, poor communication, or decreased productivity may result in termination of remote work privileges.
    """,

    """
    Company Policy: Comprehensive Vacation and Paid Time Off Benefits

    Introduction:
    We value our employees' well-being and recognize that rest and personal time are essential for maintaining productivity and job satisfaction. This comprehensive vacation policy outlines the paid time off benefits available to all eligible employees and the procedures for requesting and using vacation days.

    Vacation Day Accrual:
    Full-time employees (working 40 hours per week) receive 15 days of paid vacation per year. These days accrue on a monthly basis at a rate of 1.25 days per month, beginning from the first day of employment. Part-time employees working 20-39 hours per week receive prorated vacation benefits based on their scheduled hours. Contract workers and temporary employees are not eligible for paid vacation benefits but may take unpaid time off with manager approval.

    Tenure-Based Increases:
    Vacation accrual increases based on years of service with the company. After 3 years of continuous employment, accrual increases to 20 days per year (1.67 days per month). After 7 years, employees receive 25 days per year (2.08 days per month). After 15 years, senior employees receive 30 days per year (2.5 days per month). These increases take effect on the anniversary date of employment and apply to the entire upcoming year.

    Requesting Vacation Time:
    Employees must submit vacation requests at least 2 weeks in advance through the company HR portal for manager approval. Requests submitted with less notice may be denied if adequate coverage cannot be arranged. When submitting requests, employees should check team calendars to avoid conflicts and ensure adequate staffing levels. Multiple-week vacation requests should be submitted at least 6 weeks in advance to allow for proper planning and workload distribution.

    Approval Process:
    Direct managers are responsible for approving vacation requests based on business needs, team coverage, and project deadlines. Managers should respond to vacation requests within 3 business days of submission. If a request is denied, the manager must provide a written explanation and work with the employee to find alternative dates. Vacation requests are approved on a first-come, first-served basis when multiple employees request the same dates.

    Peak Period Restrictions:
    Vacation requests during peak business periods require additional approval from department directors. Peak periods are defined as November through December for most departments, though specific peak periods may vary by department based on business cycles. During peak periods, vacation is limited to 20% of department staff at any given time. Employees are encouraged to plan major vacations outside of these high-volume periods when possible.

    Vacation Carryover Policy:
    Unused vacation days can be carried over into the next calendar year, up to a maximum of 5 days. Any vacation days exceeding this limit will be forfeited on December 31st of each year. Employees are encouraged to use their vacation time throughout the year to maintain work-life balance. Managers should monitor employee vacation usage and encourage employees who haven't taken vacation to schedule time off.

    Vacation Payout:
    Upon termination of employment (voluntary or involuntary), employees will receive payout for all accrued but unused vacation days at their current rate of pay. This payout will be included in the final paycheck. However, vacation days cannot be cashed out while actively employed - they must be used as time off. Employees on leave of absence continue to accrue vacation days during paid leave periods but not during unpaid leave.

    Holiday Interaction:
    Company holidays do not count against vacation day balances. If a holiday falls during a scheduled vacation period, that day will not be deducted from the employee's vacation balance. The company observes 11 paid holidays annually: New Year's Day, Martin Luther King Jr. Day, Presidents' Day, Memorial Day, Independence Day, Labor Day, Thanksgiving Day, day after Thanksgiving, Christmas Eve, Christmas Day, and New Year's Eve.

    Sick Leave and Vacation:
    Sick leave and vacation are separate benefit categories. Employees should not use vacation days when they are ill - sick leave should be used instead. Employees receive 10 sick days per year in addition to vacation days. Sick leave can be used for personal illness, medical appointments, or caring for ill family members. Unlike vacation, sick leave does not carry over year to year and is not paid out upon termination.
    """,

    """
    Company Policy: Health Insurance and Wellness Benefits Program

    Program Overview:
    Our company is committed to supporting the health and wellness of our employees and their families. We offer a comprehensive benefits package that includes medical, dental, vision, mental health, and wellness programs designed to promote overall well-being and provide financial protection against healthcare costs.

    Eligibility and Enrollment:
    All full-time employees (30+ hours per week) are eligible for health insurance benefits beginning on the first day of employment. There is no waiting period - coverage is effective immediately upon hire. Part-time employees working 20-29 hours per week become eligible after 60 days of employment. New employees have 30 days from their hire date to enroll in benefits. If enrollment is not completed within this timeframe, employees must wait until the next open enrollment period unless they experience a qualifying life event.

    Medical Insurance Plans:
    The company offers three medical insurance plan options to accommodate different needs and preferences: HMO Plan (lowest premium, limited network), PPO Plan (higher premium, wider network), and High Deductible Health Plan with HSA (lowest premium, highest deductible, tax-advantaged savings).

    HMO Plan Details:
    The HMO (Health Maintenance Organization) plan offers comprehensive coverage within a defined network of providers. Employees must select a Primary Care Physician (PCP) who coordinates all care and provides referrals to specialists. Out-of-network care is not covered except in emergencies. Monthly premiums are lowest with this plan: $50 for employee-only coverage, $150 for employee plus spouse, $175 for employee plus children, and $200 for family coverage. Office visit copays are $20 for primary care and $35 for specialists. Emergency room visits have a $150 copay. Annual deductible is $500 for individuals and $1,000 for families.

    PPO Plan Details:
    The PPO (Preferred Provider Organization) plan offers greater flexibility in choosing healthcare providers. Employees can see any provider in-network without referrals and have limited out-of-network coverage (typically 70% after higher deductible). Monthly premiums: $100 for employee-only, $250 for employee plus spouse, $275 for employee plus children, and $350 for family coverage. In-network office visit copays are $25 for primary care and $45 for specialists. Out-of-network care requires meeting a higher deductible first. Annual deductible is $750 for individuals and $1,500 for families (in-network); $1,500 individual and $3,000 family (out-of-network).

    High Deductible Health Plan (HDHP):
    The HDHP is designed for employees who want lower monthly premiums and can afford higher out-of-pocket costs. This plan qualifies for a Health Savings Account (HSA) which offers triple tax advantages. Monthly premiums: $30 for employee-only, $100 for employee plus spouse, $125 for employee plus children, and $150 for family coverage. Annual deductible is $1,500 for individuals and $3,000 for families. After meeting the deductible, the plan covers 80% of costs. Maximum out-of-pocket: $3,000 individual, $6,000 family.

    Health Savings Account (HSA):
    Employees enrolled in the HDHP can contribute to an HSA, which is a tax-advantaged savings account for medical expenses. For 2025, contribution limits are $4,150 for individual coverage and $8,300 for family coverage. Employees age 55 and older can contribute an additional $1,000 catch-up contribution. The company contributes $500 annually to employee HSAs ($1,000 for family coverage). HSA funds roll over year to year and can be invested for long-term growth. Withdrawals for qualified medical expenses are tax-free.

    Dental Insurance:
    Comprehensive dental coverage is included at no additional cost to employees. The plan covers preventive care (cleanings, exams, X-rays) at 100%, basic procedures (fillings, simple extractions) at 80%, and major procedures (crowns, bridges, dentures) at 50%. Annual maximum benefit is $2,000 per person. Orthodontic coverage is available for dependent children under age 19 with a lifetime maximum of $2,000. Employees can visit any licensed dentist, though using in-network providers results in lower out-of-pocket costs.

    Vision Insurance:
    Vision coverage includes annual eye exams at $10 copay, prescription eyeglasses or contact lenses every calendar year, and discounts on LASIK surgery. Employees can choose frames up to $150 in value or contact lenses up to $150 allowance. Lens enhancements (anti-glare, scratch-resistant, progressive) are available at discounted rates. The plan covers one comprehensive eye exam per year for all family members.

    Mental Health and Counseling:
    Mental health services are covered at the same level as physical health services under all medical plans. Employees and their dependents have access to unlimited confidential counseling sessions through our Employee Assistance Program (EAP) at no cost for short-term issues. For ongoing therapy, mental health visits are covered with the same copays as medical office visits. Inpatient mental health treatment is covered at 80% after deductible. Substance abuse treatment and rehabilitation programs are also covered.

    Wellness Programs:
    The company sponsors various wellness initiatives to promote healthy lifestyles. Employees can earn up to $500 annually in wellness rewards for participating in health screenings, fitness challenges, nutrition counseling, and smoking cessation programs. Free on-site fitness center available at headquarters location. Gym membership reimbursement of up to $50/month for employees at locations without on-site facilities. Annual flu shots provided free to all employees. Quarterly wellness workshops on topics like stress management, nutrition, and financial wellness.

    Premium Cost Sharing:
    The company covers 80% of premium costs for employee-only coverage and 50% of premium costs for dependent coverage (spouse, children, or family). Premium contributions are deducted from paychecks on a pre-tax basis, reducing taxable income. Employees can change coverage levels only during open enrollment or within 30 days of a qualifying life event such as marriage, birth, adoption, or loss of other coverage.

    Open Enrollment:
    The annual open enrollment period occurs in November for coverage effective January 1st of the following year. During open enrollment, employees can change medical plans, add or remove dependents, or adjust coverage levels. Detailed plan comparison materials and decision support tools are provided. Benefits team holds information sessions and offers one-on-one consultations to help employees make informed choices.

    Dependent Coverage:
    Eligible dependents include legal spouse or domestic partner and children up to age 26 (regardless of student status, marital status, or financial dependency). Step-children and legally adopted children are also eligible. Documentation of dependent relationships must be provided during enrollment. Newborns are automatically covered for 30 days; employees must formally add them within this timeframe for continued coverage.
    """,

    """
    Company Policy: Professional Development - Learning Opportunities and Programs

    Philosophy and Commitment:
    We believe that investing in employee growth and development creates a more skilled, engaged, and innovative workforce. This policy outlines the comprehensive professional development opportunities available to employees at all levels and the procedures for accessing these resources.

    Eligible Expenses:
    The professional development budget can be used for a wide range of learning activities including but not limited to: industry conferences and seminars, technical training courses and workshops, professional certification exam fees and preparation courses, online learning platforms and courses, books and professional publications, industry association memberships, college courses directly related to current role or career progression within the company, coaching and mentoring programs, and software tools for skills development.

    Conference Attendance:
    Employees attending conferences are encouraged to share key learnings with their teams through presentations or written summaries. Conference travel expenses (transportation, lodging, meals) are covered through the regular travel budget, not the professional development budget. Employees should submit conference proposals at least 6 weeks in advance to allow for travel planning.

    Time Off for Learning:
    Employees are granted up to 5 paid days per year for attending approved training programs, conferences, or certification exams. This time does not count against vacation days. Employees should schedule learning time to minimize impact on work commitments and team deadlines. For online courses or self-paced learning, employees may use up to 3 hours per week during work hours with manager approval.

    Internal Training Programs:
    In addition to external learning opportunities, the company offers various internal training programs at no cost to employees. These include new employee orientation and onboarding, technical skills workshops, leadership development programs, mandatory compliance training, lunch-and-learn sessions, mentorship programs, and cross-functional rotation opportunities.

    Learning Management System:
    All employees have access to our learning management system (LMS) which includes thousands of online courses, video tutorials, and learning paths at no cost. Employees can track their learning progress, earn badges and certificates, and share accomplishments with their teams. Managers can assign required training and monitor team learning activity through the LMS.

    Career Development Conversations:
    Employees should discuss career goals and professional development plans with their managers during annual performance reviews and quarterly check-ins. The company encourages internal mobility and prefers to promote from within when qualified candidates are available.
    """,

    """
    Company Policy: Professional Development Budget and Reimbursement (Manager Reference)

    Annual Education Budget:
    The company provides an annual professional development budget of $2,000 per full-time employee for approved learning activities. This budget resets each calendar year on January 1st and does not roll over. Part-time employees receive a prorated budget based on their scheduled hours. Managers and senior leaders receive an enhanced budget of $3,500 annually due to increased responsibilities and need for leadership development.

    Request and Approval Process:
    Employees must submit professional development requests through the learning management system at least 3 weeks before the program start date or registration deadline. The request should include program description, learning objectives, cost breakdown, schedule, and explanation of how the learning applies to current role or career goals. Direct managers review and approve requests based on relevance to job responsibilities, employee performance, budget availability, and business needs. Requests must be approved before any expenses are incurred - retroactive approvals are not granted.

    Certification Programs:
    The company strongly supports employees pursuing industry-recognized certifications. For high-priority certifications identified by department, the company may cover costs beyond the individual professional development budget. Employees who achieve relevant certifications may receive a one-time bonus of $500 to $2,000 depending on certification difficulty and relevance. Employees must pass certification exams within 2 attempts to receive reimbursement for exam fees.

    Reimbursement Process:
    After completing an approved program, employees must submit reimbursement requests within 30 days through the expense management system with itemized receipts and proof of completion. Reimbursements are processed within 30 days of submission with complete documentation. If an employee leaves the company within 12 months of completing training that cost over $1,000, they may be required to repay a prorated portion of the expenses.

    Tuition Reimbursement:
    Separate from the professional development budget, the company offers tuition reimbursement for degree programs up to $5,250 per year (the IRS tax-free limit). Eligible degree programs must be from accredited institutions and related to the employee's current career path. Employees must maintain a minimum GPA of 3.0 to remain eligible. Reimbursement is processed after successful course completion. Employees must remain with the company for at least 2 years after completing their degree or repay tuition benefits on a prorated basis.

    Skills Gap Analysis:
    The Learning and Development team conducts periodic skills gap analyses to identify organizational training needs. High-priority skills gaps may be addressed through company-sponsored training programs or partnerships with external training providers. Department budgets are adjusted annually based on utilization rates and demonstrated business impact of learning initiatives.
    """,
]

##Step 3.1
print(f"✅ Sample documents loaded: {len(documents)} policies")
print(f"📊 Total characters: {sum(len(doc) for doc in documents):,}")
print(f"\n📋 Document lengths:")
for i, doc in enumerate(documents, 1):
    print(f"   Policy {i}: {len(doc):,} characters")

print(f"Loaded {len(documents)} documents")
print(f"Total Chars {sum(len(doc) for doc in documents)}")

##Step 3.2
# ── METADATA: Tag each document with role-based access level ──
doc_metadata = [
    {"source": "remote_work_policy",      "category": "operations", "access_role": "employee"},
    {"source": "vacation_policy",         "category": "hr",         "access_role": "employee"},
    {"source": "health_insurance_policy", "category": "benefits",   "access_role": "employee"},
    {"source": "prof_dev_general",        "category": "hr",         "access_role": "employee"},
    {"source": "prof_dev_budget_manager", "category": "hr",         "access_role": "manager"},
]
print(f"\n🏷️  Metadata assigned to {len(doc_metadata)} documents")
for i, m in enumerate(doc_metadata, 1):
    print(f"   Policy {i}: access_role='{m['access_role']}' | source='{m['source']}'")


## Step 4 - Chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""]
)

# Associate each document with its metadata
docs = [Document(page_content=documents[i], metadata=doc_metadata[i]) for i in range(len(documents))]

# Split
chunks = text_splitter.split_documents(docs)

print(f"\n✂️  CHUNKING RESULTS")
print("=" * 70)
print(f"Original documents: {len(documents)}")
print(f"Total chunks created: {len(chunks)}")
print(f"\n📋 First 3 chunks with overlap demonstration:\n")

## Step 4.2
for i in range(min(3, len(chunks))):
    print(f"Chunk {i+1} ({len(chunks[i].page_content)} chars):")
    print("-" * 70)
    print(chunks[i].page_content)
    print("\n")

    if i < 2:
        # Show overlap with next chunk
        current_end = chunks[i].page_content[-50:]
        next_start = chunks[i+1].page_content[:50]
        print(f"🔗 Overlap check:")
        print(f"   End of chunk {i+1}: ...{current_end}")
        print(f"   Start of chunk {i+2}: {next_start}...")
        print("\n")

## Step 5 - Embeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device':'cpu'}
)

# Test to get actual embedding dimension
sample_embedding = embeddings.embed_query("what is the remote work policy")

print(f"✓ Embedding model loaded: all-MiniLM-L6-v2")
print(f"✓ Embedding dimension: {len(sample_embedding)}")
print(f"{sample_embedding[:30]}")
print(f"✓ Running on: CPU")

## Step 6 - Vector Store
#Storing in vector store
vectorStore = Chroma.from_documents(
  documents=chunks,
  embedding=embeddings,
  collection_name="company_policies"
)
print(f" Vector database created!")
print(f" Stored {len(chunks)} document chunks")
print(f"{vectorStore}")

## Step 7 - Example for similarity search - demo retrieval without an LLM

query = "How do i plan remote work?"
relevant_docs = vectorStore.similarity_search(query, k=2)

print(f"🔍 Query: '{query}'")
print(f"\n📄 Top {len(relevant_docs)} relevant chunks:\n")
for i, doc in enumerate(relevant_docs, 1):
    print(f"Result {i}:")
    print(doc.page_content)
    print("-" * 80)

## Step 8 - Role-based metadata filtering

def searchWithMetaData(question, vectorstore, role, k=3):
    """
    Retrieve chunks filtered by 'access_role' metadata.
    Only chunks whose document metadata matches the given role are returned.
    """
    filter_dict = {"access_role": role}  # ChromaDB 'where' clause
    return vectorstore.similarity_search(question, k=k, filter=filter_dict)

# ── Same question, two different roles ──
question = "What training budget do I have?"
print(f"❓ Question: '{question}'")
print('=' * 70)


# Employee
print("\n👤 EMPLOYEE role (access_role='employee')")
print('-' * 70)
employee_docs = searchWithMetaData(question, vectorStore, role="employee", k=3)
if employee_docs:
    for i, doc in enumerate(employee_docs, 1):
        print(f"\nResult {i} | source: {doc.metadata.get('source')} | role: {doc.metadata.get('access_role')}")
        print(doc.page_content[:200] + '...')
else:
    print('⚠️  No documents found for this role.')


# Manager
print("\n\n👔 MANAGER role (access_role='manager')")
print('-' * 70)
manager_docs = searchWithMetaData(question, vectorStore, role="manager", k=3)
if manager_docs:
    for i, doc in enumerate(manager_docs, 1):
        print(f"\nResult {i} | source: {doc.metadata.get('source')} | role: {doc.metadata.get('access_role')}")
        print(doc.page_content[:200] + '...')
else:
    print('⚠️  No documents found for this role.')

print('\n' + '=' * 70)
print('💡 Same question — different results based on role metadata filter!')

## Step 9 -Setup the LLM

from langchain_groq import ChatGroq

from google.colab import userdata

# Retrieve the Groq API key from Colab's secrets manager

GROQ_API_KEY = userdata.get('Groq_KEY')



# Initialize Groq LLM

llm = ChatGroq(

    model="llama-3.3-70b-versatile",  # Fast, accurate, free tier

    temperature=0,  # Deterministic answers for RAG

    api_key=GROQ_API_KEY

)



print("✓ LLM loaded: Llama 3.3 70B via Groq")

print("✓ Fast inference with free API tier")

print("✓ Get your free API key at: https://console.groq.com")



# Quick test of the LLM

print("\n Testing LLM:")

print("-" * 60)

test_question = "How many days can I work remotely?"

response = llm.invoke(test_question)

print(f"Question: {test_question}")

print(f"Answer: {response.content}")

print("-" * 60)

print("✓ LLM is working!")

def ask_rag(question, vectorstore, llm, k=2, access_role=None):

    # Prepare filter if access_role is provided

    search_kwargs = {"k": k}

    if access_role:

        search_kwargs["filter"] = {"access_role": access_role}



    # Retrieve relevant documents using the retriever with potential filtering

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)

    relevant_docs = retriever.invoke(question)



    # Combine into context

    context = "\n\n".join([doc.page_content for doc in relevant_docs])



    # Create prompt

    # Modified prompt to explicitly ask for the budget amount if present

    prompt = f"""Answer the question based only on the following context. If the budget amount is specified, please provide it directly.

  Context:

  {context}

Question: {question}


Answer:"""



    # Generate answer

    answer = llm.invoke(prompt)



    return {

        "question": question,

        "answer": answer.content,

        "source_documents": relevant_docs,

        "prompt": prompt

    }

## Step 10.5 - Use RAG



question = "How many days can I work remotely?"

result = ask_rag(question, vectorStore, llm, k=2, access_role='employee')



print(f"\n Answer:\n{result['answer']}")



print(f"\n Prompt:\n{result['prompt']}")



print(f"\n Sources ({len(result['source_documents'])} documents):")

for i, doc in enumerate(result['source_documents'], 1):

    print(f"\n   Source {i}:")

    print(f"   {doc.page_content[:150]}...")

    if 'access_role' in doc.metadata:

        print(f"   Access Role: {doc.metadata['access_role']}")

## Step 11 - Another RAG use



question = "What are the health benefits?"

result = ask_rag(question, vectorStore, llm, k=3, access_role='employee')



print(f"\n Answer:\n{result['answer']}")



print(f"\n Sources ({len(result['source_documents'])} documents):")

for i, doc in enumerate(result['source_documents'], 1):

    print(f"\n   Source {i}:")

    print(f"   {doc.page_content[:150]}...")

    if 'access_role' in doc.metadata:

        print(f"   Access Role: {doc.metadata['access_role']}")


## Step 11.5 - Manager-specific RAG query



question = "What is the annual professional development budget for managers?"

result_manager = ask_rag(question, vectorStore, llm, k=5, access_role='manager')



print(f"\n Answer (Manager Role):\n{result_manager['answer']}")



print(f"\n Sources ({len(result_manager['source_documents'])} documents):")

for i, doc in enumerate(result_manager['source_documents'], 1):

    print(f"\n   Source {i}:")

    print(f"   {doc.page_content[:150]}...")

    if 'access_role' in doc.metadata:

        print(f"   Access Role: {doc.metadata['access_role']}")



## Step 12 - Evals


"""

═══════════════════════════════════════════════════════════════

STEP 1: DEFINE TEST CASES

Set up our evaluation questions and what we expect to find

═══════════════════════════════════════════════════════════════

"""



print(" SETTING UP EVALUATION TEST CASES")

print("=" * 80)



# Define test cases - just query and relevant keywords

test_cases = [

    {

        "query": "How many vacation days?",

        "keywords": ["vacation", "15 days"],

    },

    {

        "query": "Remote work policy?",

        "keywords": ["remote", "3 days"],

    },

    {

        "query": "Health insurance?",

        "keywords": ["health", "hmo", "ppo"],

    },

]

print(f"\n Created {len(test_cases)} test cases")

print("\n" + "─" * 80)



# Show what we're testing

for i, test in enumerate(test_cases, 1):

    print(f"\nTest {i}:")

    print(f"   Query: '{test['query']}'")

    print(f"   Looking for: {test['keywords']}")



print("\n" + "=" * 80)

print(" Test cases ready! Now run the evaluation metrics below.\n")

## Step 13 - EVals data



K = 5  # Get top 5 to calculate multiple metrics



# Store all results

all_results = []



for test in test_cases:

    # ONE search per query

    documents = vectorStore.similarity_search(

        test['query'], k=K) # Corrected: pass test['query'] instead of ['query']



    all_results.append({

        'query': test['query'],

        'keywords': test['keywords'],

        'documents': documents

    })



print(f" Retrieved {K} documents for {len(all_results)} queries")

print("Now you can calculate multiple metrics from this data!")

## Step 14 - Genrate EVals result

"""

Calculate Reciprocal Rank from the stored search results

"""



rr_scores = []



for result in all_results:

    query = result['query']

    keywords = result['keywords']

    documents = result['documents']



    # Find first relevant document

    found_at_rank = None



    for rank, doc in enumerate(documents, 1):

        text = doc.page_content.lower()

        has_keyword = any(kw.lower() in text for kw in keywords)



        if has_keyword:

            found_at_rank = rank

            break



    # Calculate reciprocal rank

    if found_at_rank:

        rr = 1.0 / found_at_rank

    else:

        rr = 0.0



    rr_scores.append({

        'query': query,

        'rank': found_at_rank,

        'score': rr

    })



# Calculate average

avg_rr = sum(item['score'] for item in rr_scores) / len(rr_scores)



print(f" Calculated Reciprocal Rank for {len(rr_scores)} queries")

## Step 16 - EVals Calculate Precision@K



"""

Calculate Precision@K from the stored search results

We'll calculate for K=1, K=3, and K=5

"""

# Calculate for different K values

precision_results = {

    'P@1': [],

    'P@3': [],

    'P@5': []

}



for result in all_results:

    query = result['query']

    keywords = result['keywords']

    documents = result['documents']



    # Calculate precision for different K values

    for k in [1, 3, 5]:

        # Count relevant documents in top K

        relevant_count = 0



        for doc in documents[:k]:  # Only check first k documents

            text = doc.page_content.lower()

            has_keyword = any(kw.lower() in text for kw in keywords)



            if has_keyword:

                relevant_count += 1



        # Calculate precision

        precision = relevant_count / k



        precision_results[f'P@{k}'].append({

            'query': query,

            'relevant': relevant_count,

            'total': k,

            'precision': precision

        })

# Calculate averages

avg_p1 = sum(item['precision'] for item in precision_results['P@1']) / len(precision_results['P@1'])

avg_p3 = sum(item['precision'] for item in precision_results['P@3']) / len(precision_results['P@3'])

avg_p5 = sum(item['precision'] for item in precision_results['P@5']) / len(precision_results['P@5'])



print(f" Calculated Precision@K for {len(precision_results['P@1'])} queries")