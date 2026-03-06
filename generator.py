import streamlit as st
import pandas as pd
from document_processor import process_prd_document
from rag_retriever import extract_context_from_vectorstore
from crew_setup import run_crew
from testcase_parser import parse_testcases

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Automated Test Case Generator",
    layout="wide"
)

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
.swagger-card {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 12px;
    transition: 0.3s;
}

.swagger-card:hover {
    box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
}

.badge {
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: bold;
    color: white;
    font-size: 14px;
}

.p0 { background-color: #ff4b4b; }
.p1 { background-color: #ffa500; }
.p2 { background-color: #28a745; }

.tc-title {
    font-size: 18px;
    font-weight: 600;
    margin-left: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("# ⌚ Automated Test Case Generator")

uploaded = st.file_uploader("Upload PRD (PDF)", type=["pdf"])
feature = st.text_input("Enter Feature Name")

# ---------------- GENERATE BUTTON ----------------
if st.button("Generate Test Cases"):

    if not uploaded or not feature:
        st.error("Upload PRD and enter feature.")
    else:
        with st.spinner("Processing PRD and generating test cases..."):
            vectorstore = process_prd_document(uploaded)
            context = extract_context_from_vectorstore(vectorstore, feature)
            result = run_crew(feature, context)
            testcases = parse_testcases(result)

        if testcases:
            st.success("Test cases generated successfully")

            # ----------- DISPLAY SWAGGER STYLE -----------
            for tc in testcases:

                priority_class = tc["priority"].lower()  # p0, p1, p2

                st.markdown(
                    f"""
                    <div class="swagger-card">
                        <span class="badge {priority_class}">
                            {tc['priority']}
                        </span>
                        <span class="tc-title">
                            {tc['test_case_id']} — {tc['objective']}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                with st.expander("View Details"):

                    st.markdown("### 📝 Description")
                    st.write(tc["description"])

                    st.markdown("### 🔄 Procedure")
                    for i, step in enumerate(tc["procedure"], 1):
                        st.write(f"{i}. {step}")

                    st.markdown("### ✅ Expected Result")
                    st.write(tc["expected_result"])

                    st.markdown("### 🚦 Priority")
                    st.write(tc["priority"])

            # ----------- CSV DOWNLOAD -----------
            df = pd.DataFrame(testcases)
            csv = df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="⬇ Download CSV",
                data=csv,
                file_name=f"{feature}_testcases.csv",
                mime="text/csv"
            )

        else:
            st.warning("Could not parse structured test cases. Showing raw output.")
            st.text_area("Raw Output", result, height=400)