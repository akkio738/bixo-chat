import streamlit as st
from vanna.remote import VannaDefault
import os
from datetime import datetime

# Setup Vanna
@st.cache_resource
def setup_vanna():
    vn = VannaDefault(model='bixo_chat', api_key='fcaea5a7cc08496eb79f31804da82b8e')
    vn.connect_to_sqlite('bixo.db')
    return vn

# Setup logging directory
LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'questions_log.txt') # Log file path

# Logging function
def log_question(question):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as log:
        log.write(f"{timestamp} - {question}\n")

# Page config
st.set_page_config(page_title="Bixo - Chat", page_icon="🏠", layout="wide")

# Sidebar
st.sidebar.title("Output Settings")
show_sql = st.sidebar.checkbox("Show SQL", value=False)
show_table = st.sidebar.checkbox("Show Table", value=True)
show_chart = st.sidebar.checkbox("Show Chart", value=True)
show_summary = st.sidebar.checkbox("Show Summary", value=True)
show_followup = st.sidebar.checkbox("Show Follow-up Questions", value=True)


st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">', unsafe_allow_html=True)
st.markdown('<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">', unsafe_allow_html=True)

st.markdown(
    """
    <style>
 
    .header-title {
        font-size: 2.3em;
        font-weight: bold;
        color: white;
        text-align: center;
        margin-bottom: 0;
    }
    .header-subtitle {
        font-size: 1.1em;
        color: #808080;
        text-align: center;
        margin-top: -5px;
    }
    </style>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" rel="stylesheet">
    """,
    unsafe_allow_html=True
)

# Dashboard title and subtitle
st.markdown('<div class="header-title"><i class="far fa-comment"></i> Bixo AI</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Your AI-Powered Chatbot</div>', unsafe_allow_html=True)
st.markdown("<br><br>", unsafe_allow_html=True)

# Initialize Vanna
vanna = setup_vanna()

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Main chat logic
def process_question(question):
    log_question(question)
    try:
        # Generate SQL
        sql = vanna.generate_sql(question=question, allow_llm_to_see_data=True)
        
        # Prepare response container
        response = {
            'question': question,
            'sql': sql if show_sql else None,
            'table': None,
            'chart': None,
            'chart_error': None,
            'summary': None,
            'followup_questions': None
        }
        
        # Validate and run SQL
        if vanna.is_sql_valid(sql):
            df = vanna.run_sql(sql)
            
            # Prepare table data
            if show_table:
                response['table'] = df.head(10) if len(df) > 10 else df
            
            # Generate chart
            if show_chart and vanna.should_generate_chart(df):
                try:
                    plotly_code = vanna.generate_plotly_code(question=question, sql=sql, df=df)
                    fig = vanna.get_plotly_figure(plotly_code=plotly_code, df=df)
                    response['chart'] = fig
                except Exception as e:
                    response['chart_error'] = str(e)
            
            # Generate summary
            if show_summary:
                summary = vanna.generate_summary(question=question, df=df)
                response['summary'] = summary
            
            # Generate follow-up questions
            if show_followup:
                followup_questions = vanna.generate_followup_questions(question=question, sql=sql, df=df)
                response['followup_questions'] = followup_questions
        
        # Add to chat history
        st.session_state.chat_history.append(response)
        return response
    
    except Exception as e:
        error_response = {
            'question': question,
            'error': str(e)
        }
        st.session_state.chat_history.append(error_response)
        st.error(f"An error occurred: {e}")
        return error_response

# Render chat history
def render_chat_history():
    # Render all previous entries except follow-up for last entry
    for i, entry in enumerate(st.session_state.chat_history[:-1]):
        # Render question
        st.chat_message("user").write(entry['question'])
        
        # Render response components
        if 'error' in entry:
            st.error(entry['error'])
            continue
        
        # Show SQL if enabled
        if show_sql and entry.get('sql'):
            st.code(entry['sql'], language='sql')
        
        # Show table
        if show_table and entry.get('table') is not None:
            st.dataframe(entry['table'])
        
        # Show chart
        if show_chart:
            if entry.get('chart'):
                st.plotly_chart(entry['chart'])
            elif entry.get('chart_error'):
                st.error(f"Chart generation error: {entry['chart_error']}")
        
        # Show summary
        if show_summary and entry.get('summary'):
            st.text(entry['summary'])
    
    # Render last entry with follow-up questions
    if st.session_state.chat_history:
        last_entry = st.session_state.chat_history[-1]
        
        # Render question
        st.chat_message("user").write(last_entry['question'])
        
        # Render response components
        if 'error' in last_entry:
            st.error(last_entry['error'])
            return
        
        # Show SQL if enabled
        if show_sql and last_entry.get('sql'):
            st.code(last_entry['sql'], language='sql')
        
        # Show table
        if show_table and last_entry.get('table') is not None:
            st.dataframe(last_entry['table'])
        
        # Show chart
        if show_chart:
            if last_entry.get('chart'):
                st.plotly_chart(last_entry['chart'])
            elif last_entry.get('chart_error'):
                st.error(f"Chart generation error: {last_entry['chart_error']}")
        
        # Show summary
        if show_summary and last_entry.get('summary'):
            st.text(last_entry['summary'])
        
        # Show follow-up questions only for the last entry
        if show_followup and last_entry.get('followup_questions'):
            st.subheader("Follow-up Questions")
            for fq in last_entry['followup_questions'][:5]:
                if st.button(fq):
                    process_question(fq)
                    st.rerun()

# Render initial view
render_chat_history()

# Chat input
if prompt := st.chat_input("Ask a question about your data"):
    # Process question and render results
    process_question(prompt)
    
    # Rerun to update the view
    st.rerun()