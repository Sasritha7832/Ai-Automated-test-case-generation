import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from logger import get_logger

logger = get_logger(__name__)

class DashboardAnalytics:
    """Generates charts and metrics for the Streamlit UI."""
    
    @staticmethod
    def get_test_case_distribution(df: pd.DataFrame):
        try:
            if df.empty or 'test_type' not in df.columns:
                return None
            
            # Count test types
            counts = df['test_type'].value_counts().reset_index()
            counts.columns = ['Test Type', 'Count']
            
            fig = px.pie(
                counts, 
                names='Test Type', 
                values='Count',
                title="Test Case Type Distribution",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            return fig
        except Exception as e:
            logger.error(f"Error generating test case distribution chart: {str(e)}")
            return None

    @staticmethod
    def get_priority_distribution(df: pd.DataFrame):
        try:
            if df.empty or 'priority' not in df.columns:
                return None
                
            counts = df['priority'].value_counts().reset_index()
            counts.columns = ['Priority', 'Count']
            
            # Sort P0 -> P3
            counts['Priority'] = counts['Priority'].astype(str)
            
            fig = px.bar(
                counts, 
                x='Priority', 
                y='Count', 
                color='Priority',
                title="Test Cases by Priority",
                text='Count'
            )
            return fig
        except Exception as e:
            logger.error(f"Error generating priority distribution chart: {str(e)}")
            return None

    @staticmethod
    def get_risk_distribution(risk_preds: list):
        """Expects a list of predicted Risk labels (High, Medium, Low)"""
        try:
            logger.info("Generating risk distribution chart")
            if not risk_preds:
                return None
                
            counts = pd.Series(risk_preds).value_counts().reset_index()
            counts.columns = ['Risk', 'Count']
            
            color_map = {
                "High": "#ff4b4b",
                "Medium": "#ffa500",
                "Low": "#28a745",
                "Unknown": "gray"
            }
            
            fig = px.bar(
                counts,
                x='Risk',
                y='Count',
                color='Risk',
                color_discrete_map=color_map,
                title="Module-wise Bug Risk Predictions"
            )
            return fig
        except Exception as e:
            logger.error(f"Error generating risk distribution chart: {str(e)}")
            return None

    @staticmethod
    def get_complexity_distribution(complexity_scores: list):
        """Expects a list of integer Complexity Scores (0-100)"""
        try:
            logger.info("Generating complexity distribution chart")
            if not complexity_scores:
                return None
                
            df = pd.DataFrame({'Score': complexity_scores})
            
            fig = px.histogram(
                df, 
                x='Score', 
                nbins=10, 
                title="Requirement Complexity Score Distribution",
                color_discrete_sequence=['#17a2b8']
            )
            fig.update_layout(xaxis_title="Complexity Score", yaxis_title="Number of Chunks")
            return fig
        except Exception as e:
            logger.error(f"Error generating complexity distribution chart: {str(e)}")
            return None
            
    @staticmethod
    def get_ml_metrics_radar(accuracy=0.85, precision=0.82, recall=0.80, f1=0.81):
        """Displays a radar chart for the Bug Risk ML Model Performance metrics."""
        try:
            categories = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                  r=[accuracy, precision, recall, f1],
                  theta=categories,
                  fill='toself',
                  name='Model Performance',
                  marker=dict(color='#8A2BE2')
            ))
            
            fig.update_layout(
              polar=dict(
                radialaxis=dict(
                  visible=True,
                  range=[0, 1]
                )),
              showlegend=False,
              title="Bug Risk Model Evaluation Metrics"
            )
            
            return fig
        except Exception as e:
            logger.error(f"Error drawing radar chart: {e}")
            return None

    @staticmethod
    def get_coverage_heatmap(prd_sentences: list, test_cases: list, rtm_mapping: list = None):
        """Generates a density heatmap of Semantic Coverage across PRD modules and generated cases."""
        try:
            if not prd_sentences or not test_cases:
                return None
                
            logger.info("Generating Test Coverage Heatmap")
            
            heat_data = []
            if rtm_mapping:
                for req in rtm_mapping:
                    req_id = req.get("req_id", "REQ")
                    links = req.get("linked_test_cases", [])
                    if links:
                        # Find the test types of the linked cases
                        for link in links:
                            tc_id = link.get("id")
                            tc_obj = next((tc for tc in test_cases if tc.get("test_case_id") == tc_id), None)
                            if tc_obj:
                                heat_data.append({
                                    "Requirement_Index": req_id,
                                    "Test_Type": tc_obj.get("test_type", "Functional"),
                                    "Coverage_Intensity": link.get("similarity", 0.5) * 5
                                })
                    else:
                        heat_data.append({
                            "Requirement_Index": req_id,
                            "Test_Type": "Uncovered",
                            "Coverage_Intensity": 0
                        })
            else:
                return None

            if not heat_data:
                return None

            df_heat = pd.DataFrame(heat_data)
            
            fig = px.density_heatmap(
                df_heat,
                x="Requirement_Index",
                y="Test_Type",
                z="Coverage_Intensity",
                title="Requirements vs Scenarios Coverage",
                labels={
                    "Requirement_Index": "Requirement ID",
                    "Test_Type": "Test Scenario Type",
                    "Coverage_Intensity": "Coverage Depth"
                },
                color_continuous_scale="Viridis",
                histfunc="sum"
            )
            return fig
        except Exception as e:
            logger.error(f"Error drawing coverage heatmap: {e}")
            return None

    @staticmethod
    def get_qa_intelligence_gauge(score: float, title: str = "QA Intelligence Score"):
        """Generates a Plotly Gauge chart for the overall QA Intelligence Score."""
        try:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                title={'text': title},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 60], 'color': "lightgray"},
                        {'range': [60, 80], 'color': "gray"},
                        {'range': [80, 100], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            return fig
        except Exception as e:
            logger.error(f"Error generating QA Intelligence gauge: {e}")
            return None

    @staticmethod
    def get_bug_risk_trends(history_data: list):
        """Generates a line chart showing bug risk trends over time/sessions."""
        try:
            if not history_data:
                return None
            
            # history_data should be a list of dicts: [{'session': 1, 'risk': 45}, ...]
            df = pd.DataFrame(history_data)
            if 'session' not in df.columns or 'risk' not in df.columns:
                 return None
                 
            fig = px.line(df, x='session', y='risk', title='Bug Risk Trend Across QA Runs',
                          markers=True, line_shape='spline')
            fig.update_layout(xaxis_title="QA Run", yaxis_title="Average Bug Risk (%)")
            return fig
        except Exception as e:
             logger.error(f"Error generating bug risk trends: {e}")
             return None
