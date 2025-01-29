import streamlit as st
import pandas as pd
import db_dtypes
from google.cloud import bigquery
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Initialize connection to BigQuery
def init_bigquery():
    CREDENTIAL_PATH = os.environ.get("CREDENTIAL_PATH")
    client = bigquery.Client()
    return client

# Query collisions data by borough
# @st.cache_data  # cache the result to improve performance
def get_collision_ts(client, start_date, end_date):
    start = start_date.strftime('%Y-%m-%d')
    end = end_date.strftime('%Y-%m-%d')
    query = f"""
        select 
            crash_date,
            count(*) as people_involved, count(distinct collision_id) as crashes
        from `nyc-transit-426211.motor_vehicle_crashes.person`
        where crash_date BETWEEN '{start}' AND '{end}'
        group by 1
        order by 1 asc;
    """

    query_job = client.query(query)
    return query_job.to_dataframe()

def get_lat_long_data(client, start_date, end_date):
    "Refer to this: https://plotly.com/python/tile-scatter-maps/"
    start = start_date.strftime('%Y-%m-%d')
    end = end_date.strftime('%Y-%m-%d')
    query = f"""
        select
            latitude, longitude,
            case
                when crash_hour>=0 and crash_hour<6 then '0-5'
                when crash_hour>=6 and crash_hour<12 then '6-11'
                when crash_hour>=12 and crash_hour<18 then '12-17'
                else '18-23'
            end as crash_hour_range
        from (
            select 
                latitude, longitude, 
                CAST(SPLIT(crash_time, ':')[SAFE_OFFSET(0)] AS INT64) as crash_hour
            from `nyc-transit-426211.motor_vehicle_crashes.crashes`
            where crash_date BETWEEN '{start}' AND '{end}'
            and latitude is not null
            and latitude != 0
        );
    """
    query_job = client.query(query)
    return query_job.to_dataframe()

def get_collision_data(client, start_date, end_date):
    start = start_date.strftime('%Y-%m-%d')
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
            from `nyc-transit-426211.motor_vehicle_crashes.crashes`
            where crash_date BETWEEN '{start}' AND '{end}'
            and latitude is not null
            and latitude != 0
        ) c
        left join (
            select collision_id, count(*) as people_involved
            from `nyc-transit-426211.motor_vehicle_crashes.person`
            where crash_date BETWEEN '{start}' AND '{end}'
            group by 1
        ) p
        on c.collision_id = p.collision_id;
    """
    query_job = client.query(query)
    return query_job.to_dataframe()


# Main function to run the app
def main():
    st.title("NYC Pedestrian Collisions")

    # Initialize BigQuery Client
    client = init_bigquery()

    # Date filter widgets
    st.sidebar.header("Filter by Date Range")
    start_date = st.sidebar.date_input("Start Date", datetime.today() - timedelta(days=61))
    # have data only up until 60 days ago
    end_date = st.sidebar.date_input("End Date", datetime.today() - timedelta(days=60))

    # Ensure start_date is before end_date
    if start_date > end_date:
        st.error("Error: End date must fall after start date.")
    else:
        # Get filtered data from BigQuery
        # df = get_collision_ts(client, start_date, end_date)

        # # Display the dataframe
        # st.dataframe(df)

        # Create the figure using Plotly graph_objects
        # fig = go.Figure()

        # # Add trace for collisions
        # fig.add_trace(go.Scatter(
        #     x=pd.to_datetime(df['crash_date']), 
        #     y=df['crashes'], 
        #     mode='lines',
        #     name='Crashes',
        #     line=dict(color='blue')
        # ))

        # # Add trace for People
        # fig.add_trace(go.Scatter(
        #     x=pd.to_datetime(df['crash_date']), 
        #     y=df['people_involved'], 
        #     mode='lines',
        #     name='People Involved',
        #     line=dict(color='orange')
        # ))

        # # Customize the layout of the plot
        # fig.update_layout(
        #     title="NYC Pedestrian Collisions and Accidents Over Time",
        #     xaxis_title="Date",
        #     yaxis_title="Count",
        #     yaxis=dict(
        #         autorange=True,
        #         autorangeoptions=dict(
        #             minallowed=0
        #         )
        #     ),
        #     legend_title="Metrics",
        #     hovermode="x unified"  # Combine hover info for both traces
        # )

        # # Display the plot
        # st.plotly_chart(fig, use_container_width=True)
        
        # # map
        # map_df = get_lat_long_data(client, start_date, end_date)
        # # st.map(map_df)
    
        # # plotly map
        # fig2 = px.scatter_mapbox(map_df, 
        #                          lat="latitude",
        #                          lon="longitude",
        #                          color="crash_hour_range",
        #                          color_continuous_scale=px.colors.cyclical.IceFire
        #                          )
        # fig2.update_layout(mapbox_style='carto-positron')
        # st.plotly_chart(fig2, on_select="rerun", selection_mode="points")
        
        # map2
        map_df2 = get_collision_data(client, start_date, end_date)

        # Add a radio button widget to filter by person_injury
        st.sidebar.header("Filter by Injury Type")
        injury_filter = st.sidebar.radio(
            "Select Injury Type",
            options=["All", "Injury", "Injury+Death", "Death", "Unspecified"],
            index=0 # Default selection
        )
        
        # Apply the filter to the df
        if injury_filter != 'All':
            map_df2 = map_df2[map_df2["person_injury"] == injury_filter]
    
        # plotly map
        fig3 = px.scatter_mapbox(
            map_df2,
            title="Crashes",
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

# TODO
# simplify a few more graphs, break out by borough
# list injury type over time
# include a map
# predict number of crahses?

# -- 2024-09-13
# -- 344 total
# -- 316 where lat is null or long is null
# -- 95 where on_street_name is null
# -- 168 where off_street_name is null
# -- where off_street_name is null and latitude is null: 140
# -- so we can only potentially locate 344 - 140 = 204 crashes (59%) hmm
# is this missing data the same for older dates? check january;