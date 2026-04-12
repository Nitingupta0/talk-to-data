# src/response/charts.py
import plotly.express as px
import pandas as pd

def generate_chart(df, intent, query=""):
    """Dynamically routes to the best Plotly chart, supporting all major types."""
    
    # Check if we actually have data to plot
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    
    # ✨ DEFENSIVE FIX: Ensure query is ALWAYS a string before making it lowercase ✨
    if query is None:
        query = ""
    
    query_lower = query.lower() # Now this is perfectly safe!

    # Special case: If it's a 1-column dataframe and they want a histogram
    if len(df.columns) == 1 and "histogram" in query.lower():
        return px.histogram(df, x=df.columns[0], title=f"Distribution of {df.columns[0]}")
        
    # We need at least 2 columns for most charts
    if len(df.columns) < 2:
        return None
    
    # Grab the first two columns to use as X and Y
    x_col = df.columns[0] 
    y_col = df.columns[1] 
    query_lower = query.lower()
    
    try:
        fig = None
        
        # --- 1. EXPLICIT USER OVERRIDES ---
        if "pie" in query_lower:
            fig = px.pie(df, names=x_col, values=y_col, title=f"{y_col} by {x_col}", hole=0.3)
            
        elif "line" in query_lower:
            fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}", markers=True)
            
        elif "bar" in query_lower:
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}", color=x_col)
            
        elif "scatter" in query_lower:
            fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}", size=y_col, color=x_col)
            
        elif "box" in query_lower:
            fig = px.box(df, x=x_col, y=y_col, title=f"Distribution of {y_col} by {x_col}", color=x_col)
            
        elif "histogram" in query_lower:
            fig = px.histogram(df, x=x_col, y=y_col, title=f"Histogram of {y_col} grouped by {x_col}", color=x_col)
            
        elif "area" in query_lower:
            fig = px.area(df, x=x_col, y=y_col, title=f"Area Chart: {y_col} over {x_col}")
            
        elif "violin" in query_lower:
            fig = px.violin(df, x=x_col, y=y_col, title=f"Violin Plot of {y_col} by {x_col}", color=x_col, box=True)
            
        elif "funnel" in query_lower:
            fig = px.funnel(df, x=x_col, y=y_col, title=f"Funnel Analysis: {y_col} by {x_col}")
            
        elif "heatmap" in query_lower or "density" in query_lower:
            fig = px.density_heatmap(df, x=x_col, y=y_col, title=f"Density Heatmap: {x_col} vs {y_col}")
            
        elif "radar" in query_lower or "spider" in query_lower:
            fig = px.line_polar(df, r=y_col, theta=x_col, line_close=True, title=f"Radar Chart of {y_col}")

        # --- 2. INTENT DEFAULTS ---
        elif intent == "breakdown":
            fig = px.pie(df, names=x_col, values=y_col, title=f"Breakdown of {y_col} by {x_col}", hole=0.3)
        elif intent in ["change_analysis", "prediction"]:
            fig = px.line(df, x=x_col, y=y_col, title=f"Trend of {y_col} over {x_col}", markers=True)
        else:
            fig = px.bar(df, x=x_col, y=y_col, title=f"Comparison of {y_col} by {x_col}", color=x_col)

        return chart_to_dict(fig)
            
    except Exception as e:
        print(f"Chart generation error: {e}") 
        return None

def chart_to_dict(fig):
    """Convert plotly figure to JSON-serializable dict for session state storage."""
    if fig is None:
        return None
    return fig.to_dict()