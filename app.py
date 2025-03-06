import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Must be the first Streamlit command
st.set_page_config(layout="wide", page_title="Demo Service Company Dashboard")

st.markdown("""
    <style>
    body {font-family: 'Roboto', sans-serif;}
    .stApp {background-color: #fafafa;}
    </style>
""", unsafe_allow_html=True)

# Try to import data.py, with fallback if it fails
try:
    from data import attribution_data, orders_data, pricing_sent_data
except Exception as e:
    st.error(f"Error importing data.py: {e}")
    attribution_data = pd.DataFrame()
    orders_data = pd.DataFrame()
    pricing_sent_data = pd.DataFrame()

# Helper function for table formatting
def format_table_data(df):
    if df.empty:
        return df
    df = df.copy()
    for col in ["Total Job Amount", "Campaign Cost", "Cost per Lead", "Order Total"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"${int(x):,}")
    for col in ["Conversion Rate", "Booking Rate"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{int(x * 100)}%")
    if "ROI" in df.columns:
        df["ROI"] = df["ROI_numeric"].apply(lambda x: f"{int(x * 100)}%")
    return df

# Prepare data with debug checks
def prepare_data(start_month, end_month, aggregation_type):
    st.write("Preparing data...")
    if attribution_data.empty:
        st.warning("Attribution data is empty!")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    all_months = sorted(attribution_data["YearMonth"].unique(), 
                        key=lambda x: pd.to_datetime(x, format="%b. %Y", errors="coerce"))
    st.write(f"All months: {all_months}")
    start_idx = all_months.index(start_month)
    end_idx = all_months.index(end_month)
    selected_months = all_months[start_idx:end_idx + 1]
    st.write(f"Selected months: {selected_months}")

    # Filter Attribution Data
    filtered_attr = attribution_data[attribution_data["YearMonth"].isin(selected_months)]
    st.write(f"Filtered attribution data shape: {filtered_attr.shape}")
    agg_key = "Source" if aggregation_type == "source" else "Display Source"
    agg_data = filtered_attr.groupby(agg_key)[["Inquiries", "Pricing Sent", "Orders", "Paid Orders", 
                                               "Total Job Amount", "Campaign Cost"]].sum().reset_index()
    agg_data["Cost per Lead"] = (agg_data["Campaign Cost"] / agg_data["Inquiries"]).fillna(0).round(0)
    agg_data["Conversion Rate"] = (agg_data["Orders"] / agg_data["Pricing Sent"]).fillna(0).round(2)
    agg_data["Booking Rate"] = (agg_data["Pricing Sent"] / agg_data["Inquiries"]).fillna(0).round(2)
    agg_data["ROI_numeric"] = ((agg_data["Total Job Amount"] - agg_data["Campaign Cost"]) / 
                               agg_data["Campaign Cost"]).fillna(0).round(2)
    agg_data["ROI"] = agg_data["ROI_numeric"].apply(lambda x: f"{int(x * 100)}%")
    agg_data["Month"] = f"{start_month} - {end_month}" if start_month != end_month else start_month
    agg_data["Display Source"] = agg_data[agg_key]

    # Monthly Data
    monthly_agg = filtered_attr.groupby("YearMonth")[["Inquiries", "Orders", "Campaign Cost", "Total Job Amount"]].sum().reset_index()
    monthly_agg = monthly_agg.rename(columns={"Orders": "New Orders"})
    monthly_agg = monthly_agg.merge(pricing_sent_data, on="YearMonth", how="left")
    monthly_agg["Pricing Sent"] = monthly_agg["Pricing Sent"].fillna(0).round(0)
    monthly_agg = monthly_agg.merge(orders_data.groupby("YearMonth")["Order Total"].sum().reset_index(), on="YearMonth", how="left")
    monthly_agg["Order Total"] = monthly_agg["Order Total"].fillna(0).round(0)
    monthly_agg["Total Orders"] = orders_data.groupby("YearMonth").size().reindex(monthly_agg["YearMonth"], fill_value=0).values
    monthly_agg["Cost per Lead"] = (monthly_agg["Campaign Cost"] / monthly_agg["Inquiries"]).fillna(0).round(0)
    monthly_agg["Conversion Rate"] = (monthly_agg["New Orders"] / monthly_agg["Pricing Sent"]).fillna(0).round(2)
    monthly_agg["Booking Rate"] = (monthly_agg["Pricing Sent"] / monthly_agg["Inquiries"]).fillna(0).round(2)
    monthly_agg["ROI_numeric"] = ((monthly_agg["Total Job Amount"] - monthly_agg["Campaign Cost"]) / 
                                  monthly_agg["Campaign Cost"]).fillna(0).round(2)
    monthly_agg["ROI"] = monthly_agg["ROI_numeric"].apply(lambda x: f"{int(x * 100)}%")
    
    # Fix the sorting logic for YearMonth
    def parse_date(date_str):
        try:
            return pd.to_datetime(date_str, format="%b. %Y")
        except:
            return pd.to_datetime(date_str, format="mixed")
    
    monthly_agg = monthly_agg.sort_values("YearMonth", key=lambda x: x.apply(parse_date))

    # Revenue Data
    filtered_orders = orders_data[orders_data["YearMonth"].isin(selected_months)]
    revenue_by_yearmonth = filtered_orders.groupby("YearMonth")["Order Total"].sum().reset_index()

    return agg_data, monthly_agg, revenue_by_yearmonth

st.title("Demo Service Company Dashboard")

# Check if data is loaded
if attribution_data.empty:
    st.error("No data loaded from data.py. Please check data.py and credentials.")
else:
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        # Get unique months and sort them chronologically
        unique_months = sorted(attribution_data["YearMonth"].unique(), 
                             key=lambda x: pd.to_datetime(x, format="%b. %Y"))
        # Find May 2024 index if it exists, otherwise use 0
        may_2024_index = unique_months.index("May. 2024") if "May. 2024" in unique_months else 0
        start_month = st.selectbox("Start Month", unique_months, index=may_2024_index)
    with col2:
        end_month = st.selectbox("End Month", unique_months, index=len(unique_months)-1)
    with col3:
        agg_type = st.selectbox("Aggregation", ["Source", "Campaign"], index=0)
    aggregation_type = "source" if agg_type == "Source" else "campaign"

    # Prepare data
    agg_data, monthly_agg, revenue_by_yearmonth = prepare_data(start_month, end_month, aggregation_type)

    # Debug info
    st.sidebar.write("Data Range Info:")
    st.sidebar.write(f"Start Month: {start_month}")
    st.sidebar.write(f"End Month: {end_month}")
    st.sidebar.write(f"Available Months: {unique_months}")

    # Key Metrics
    st.header("Key Metrics")
    if not agg_data.empty:
        # Calculate total metrics
        total_revenue = revenue_by_yearmonth["Order Total"].sum()
        total_inquiries = agg_data["Inquiries"].sum()
        total_orders = monthly_agg["Total Orders"].sum()  # Use the total orders from monthly_agg
        total_pricing_sent = agg_data["Pricing Sent"].sum()
        total_attributed_orders = agg_data["Orders"].sum()  # Get attributed orders
        avg_cost_per_lead = (agg_data["Campaign Cost"].sum() / total_inquiries).round(0)
        conversion_rate = ((total_attributed_orders / total_pricing_sent) * 100).round(1)  # Use attributed orders
        booking_rate = ((total_pricing_sent / total_inquiries) * 100).round(1)
        
        # Create metrics display
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Revenue",
                value=f"${int(total_revenue):,}",
                delta=None
            )
        
        with col2:
            st.metric(
                label="Total Inquiries",
                value=f"{int(total_inquiries):,}",
                delta=None
            )
        
        with col3:
            st.metric(
                label="Total Orders",
                value=f"{int(total_orders):,}",
                delta=None
            )
        
        with col4:
            st.metric(
                label="Pricing Sent",
                value=f"{int(total_pricing_sent):,}",
                delta=None
            )
        
        # Second row of metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Cost per Lead",
                value=f"${int(avg_cost_per_lead):,}",
                delta=None
            )
        
        with col2:
            st.metric(
                label="Conversion Rate",
                value=f"{conversion_rate}%",
                delta=None
            )
        
        with col3:
            st.metric(
                label="Booking Rate",
                value=f"{booking_rate}%",
                delta=None
            )
        
        with col4:
            st.metric(
                label="Period",
                value=f"{start_month} - {end_month}" if start_month != end_month else start_month,
                delta=None
            )
    else:
        st.warning("No metrics data to display.")

    # Monthly Revenue Trend
    st.header("Monthly Revenue Trend")
    if not revenue_by_yearmonth.empty:
        # Sort the data chronologically
        revenue_by_yearmonth = revenue_by_yearmonth.sort_values(
            "YearMonth", 
            key=lambda x: pd.to_datetime(x, format="%b. %Y")
        )
        
        # Create revenue trend line chart using Plotly
        fig_trend = go.Figure(data=[go.Scatter(
            x=revenue_by_yearmonth["YearMonth"],
            y=revenue_by_yearmonth["Order Total"],
            mode='lines+markers+text',
            text=revenue_by_yearmonth["Order Total"].apply(lambda x: f"${int(x):,}"),
            textposition="top center",
        )])
        fig_trend.update_layout(
            title="Monthly Revenue Trend",
            height=400,
            showlegend=False,
            yaxis_title="Revenue ($)",
            yaxis=dict(tickformat="$,.0f"),
            xaxis_title="Month"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.warning("No revenue trend data to display.")

    # Marketing Attribution
    st.header("Marketing Attribution")
    col1, col2 = st.columns(2)

    with col1:
        if not agg_data.empty:
            # Create a single pie chart for sources/campaigns
            fig_sources = go.Figure(data=[go.Pie(
                labels=agg_data["Display Source"],
                values=agg_data["Inquiries"],
                hole=.3,
                textinfo='label+percent+value',
                marker=dict(colors=px.colors.qualitative.Set3)
            )])
            fig_sources.update_layout(
                title="Inquiries by Source/Campaign",
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_sources, use_container_width=True)
        else:
            st.warning("No attribution data to display.")

    with col2:
        if not agg_data.empty:
            # Create horizontal bar chart for funnel progression
            # Calculate total values for each stage
            total_inquiries = agg_data["Inquiries"].sum()
            total_pricing = agg_data["Pricing Sent"].sum()
            total_orders = agg_data["Orders"].sum()
            total_paid = agg_data["Paid Orders"].sum()
            
            # Create the funnel data
            stages = ["Inquiries", "Pricing Sent", "Orders", "Paid Orders"]
            values = [total_inquiries, total_pricing, total_orders, total_paid]
            
            # Calculate percentages
            percentages = [(v / total_inquiries * 100).round(1) for v in values]
            
            # Create the horizontal bar chart
            fig_funnel = go.Figure(go.Bar(
                x=values,
                y=stages,
                orientation='h',
                text=[f"{v:,} ({p}%)" for v, p in zip(values, percentages)],
                textposition='auto',
                marker_color=px.colors.qualitative.Set3[0]
            ))
            
            fig_funnel.update_layout(
                title="Marketing Funnel Progression",
                height=400,
                showlegend=False,
                xaxis_title="Count",
                yaxis_title="Stage",
                xaxis=dict(tickformat=",d")
            )
            
            st.plotly_chart(fig_funnel, use_container_width=True)
        else:
            st.warning("No funnel data to display.")

    # Monthly Summary
    st.header("Monthly Summary")
    if not monthly_agg.empty:
        # Sort the data chronologically
        monthly_agg = monthly_agg.sort_values(
            "YearMonth", 
            key=lambda x: pd.to_datetime(x, format="%b. %Y")
        )
        st.dataframe(format_table_data(monthly_agg), use_container_width=True)
    else:
        st.warning("No monthly data to display.")

    # Source/Campaign Summary
    st.header(f"{agg_type} Summary")
    if not agg_data.empty:
        st.dataframe(format_table_data(agg_data), use_container_width=True)
    else:
        st.warning("No summary data to display.")

if __name__ == "__main__":
    st.write("Streamlit app running...")