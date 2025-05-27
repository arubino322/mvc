import os
from datetime import datetime, timedelta

import db_dtypes
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
DATASET = os.getenv("BASE_PATH")

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)

# Query collisions data by borough
@st.cache_data(ttl=600)
def get_most_recent_day(end_date):
    end = end_date.strftime('%Y-%m-%d')
    query = f"""
        select crashes, round(yhat) as yhat, round(crashes - yhat) as delta
        from `{GOOGLE_CLOUD_PROJECT}.{DATASET}.predictions` p
        left join (
            select
            crash_date,
            count(distinct collision_id) as crashes,
            from `{GOOGLE_CLOUD_PROJECT}.{DATASET}.crashes`
            where crash_date = '{end}'
            group by 1
        ) c
        on p.ds = c.crash_date
        where ds='{end}';
    """
    query_job = client.query(query)
    return query_job.to_dataframe()

@st.cache_data(ttl=600)
def get_collision_ts( start_date, end_date):
    start = start_date.strftime('%Y-%m-%d')
    end = end_date.strftime('%Y-%m-%d')
    query = f"""
        select 
            crash_date,
            people_involved,
            ifnull(round(crashes), 0) as crashes,
            ifnull(round(yhat), 0) as yhat,
            ifnull(yhat_lower, 0) as lower_bound,
            ifnull(yhat_upper, 0) as upper_bound
        from (
            select crash_date,
            count(*) as people_involved,
            count(distinct collision_id) as crashes
            from `{GOOGLE_CLOUD_PROJECT}.{DATASET}.person`
            where crash_date BETWEEN '{start}' AND '{end}'
            group by 1
        ) p1
        left join (
            select *
            from `{GOOGLE_CLOUD_PROJECT}.{DATASET}.predictions`
        ) p2
        on p1.crash_date=p2.ds
        order by 1 asc;
    """
    query_job = client.query(query)
    return query_job.to_dataframe()

@st.cache_data(ttl=600)
def get_collision_data(end_date):
    # start = start_date.strftime('%Y-%m-%d')
    end = end_date.strftime('%Y-%m-%d')
    query = f"""
        select 
            c.collision_id, crash_time, latitude, longitude,
            ifnull(people_involved, 0) as people_involved,
            number_of_persons_injured, number_of_persons_killed,
            case
                when number_of_persons_injured > 0 and number_of_persons_killed = 0 then 'Injury'
                when number_of_persons_injured > 0 and number_of_persons_killed > 0 then 'Injury+Death'
                when number_of_persons_injured = 0 and number_of_persons_killed > 0 then 'Death'
                else 'Unspecified'
            end as person_injury
        from (
            select collision_id, crash_time, latitude, longitude,
                number_of_persons_injured,
                number_of_persons_killed,
            from `{GOOGLE_CLOUD_PROJECT}.{DATASET}.crashes`
            where crash_date = '{end}'
            and latitude is not null
            and latitude != 0
        ) c
        left join (
            select collision_id, count(*) as people_involved
            from `{GOOGLE_CLOUD_PROJECT}.{DATASET}.person`
            where crash_date = '{end}'
            group by 1
        ) p
        on c.collision_id = p.collision_id;
    """
    query_job = client.query(query)
    return query_job.to_dataframe()


def main():
    # Date filter widgets
    st.sidebar.header("Filter by Date Range")
    start_date = st.sidebar.date_input("Start Date", "2025-01-01")
    # have data only up until 60 days ago
    end_date = st.sidebar.date_input("End Date", datetime.today() - timedelta(days=61))
    
    st.title("NYC Pedestrian Collisions")
    st.subheader(f"Most recent data as of {end_date}")

    # Ensure start_date is before end_date
    if start_date > end_date:
        st.error("Error: End date must fall after start date.")
    else:
        ##### MOST RECENT DAY DATA #####
        last_day = get_most_recent_day(end_date)
        
        # tiles at the top
        col1, col2, col3 = st.columns(3)
        col1.metric("Actual", int(last_day['crashes'][0]), border=True)
        col2.metric("Predicted", int(last_day['yhat'][0]), border=True)
        col3.metric("Delta %", f"{last_day['delta'][0]}%", border=True)
        
        ###### TIME SERIES #####
        df = get_collision_ts(start_date, end_date)

        # Create the figure using Plotly graph_objects
        fig = go.Figure()

        # Add trace for collisions
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(df['crash_date']),
            y=df['crashes'],
            mode='lines',
            name='Actual',
            line=dict(color='orange', width=2)
        ))
        
        # Trace for UB & LB
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(df['crash_date']),
            y=df['yhat'],
            mode='lines+markers',
            name='Predicted',
            line=dict(color='blue', width=2)
        ))

        # upper bound
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(df['crash_date']),
            y=df['upper_bound'],
            mode='lines',
            name='Upper Bound',
            line=dict(color='gray', width=1, dash='dash')
        ))
        
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(df['crash_date']),
            y=df['lower_bound'],
            mode='lines',
            name='Lower Bound',
            line=dict(color='gray', width=1, dash='dash')
        ))

        # Customize the layout of the plot
        fig.update_layout(
            title="NYC Pedestrian Collisions and Accidents Over Time",
            xaxis_title="Date",
            yaxis_title="Count",
            yaxis=dict(
                autorange=True,
                autorangeoptions=dict(
                    minallowed=0
                )
            ),
            legend_title="Metrics",
            hovermode="x unified"  # Combine hover info for both traces
        )

        # Display the plot
        st.plotly_chart(fig, use_container_width=True)
        
        ##### MAP #####
        map_df = get_collision_data(end_date)

        # plotly map
        fig3 = px.scatter_map(
            map_df,
            title=f"Crashes on {end_date}",
            lat="latitude",
            lon="longitude",
            size="people_involved",
            size_max=10,
            zoom=9,
            color_discrete_sequence=["black"],
            opacity=0.5,
            hover_data={"people_involved": True, "latitude": False, "longitude": False}
        )
        fig3.update_layout(
            mapbox_style='open-street-map',
            width=800,
            height=600
        )
        st.plotly_chart(fig3, on_select="rerun", selection_mode="points")

# Run the app
if __name__ == '__main__':
    main()
