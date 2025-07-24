import pandas as pd
import streamlit as st

# Set up the app
st.set_page_config(page_title="AHS Contractor Assignment", layout="wide")
st.title("📊 AHS Contractor Assignment App")

# File uploaders
ahs_workplan_file = st.file_uploader("Upload AHS Workplan Excel", type=["xlsx"])
case_list_file = st.file_uploader("Upload Case List Excel", type=["xlsx"])  # Renamed for clarity

if ahs_workplan_file and case_list_file:
    ahs_workplan_df = pd.read_excel(ahs_workplan_file)
    case_list_df = pd.read_excel(case_list_file)

    # Create unique identifier
    case_list_df['villageidentifier'] = case_list_df['district'].str.title() + "_" + case_list_df['cluster'].str.title() + "_" + case_list_df['village'].str.title()
    ahs_workplan_df['villageidentifier'] = ahs_workplan_df['District'].str.title() + "_" + ahs_workplan_df['Cluster'].str.title() + "_" + ahs_workplan_df['Villages'].str.title()

    # Merge data
    merged_df = case_list_df.merge(
        ahs_workplan_df[['villageidentifier', 'DAY', 'DATE', 'Contractors Code']],
        on='villageidentifier',
        how='left'
    )

    # Drop duplicated IDs
    merged_df.drop_duplicates(subset='id', keep='first', inplace=True)

    # Logic columns
    merged_df['contractor_codes'] = merged_df['Contractors Code'].str.split(',')
    merged_df['priority'] = merged_df['status'].map({'Target': 1, 'Reserve': 2}).fillna(3)

    # Contractor assignment logic
    def assign_contractor(codes, index):
        if not isinstance(codes, list) or not codes:
            return "Not Assigned"
        clean = [c.strip() for c in codes]
        return clean[(index - 1) % len(clean)]

    def process_group(group):
        group = group.sort_values('priority').copy()
        group['target_row'] = (group['status'] == 'Target').cumsum()
        group['reserve_row'] = (group['status'] == 'Reserve').cumsum()
        group['other_row'] = (~group['status'].isin(['Target', 'Reserve'])).cumsum()

        group['assigned_contractor'] = [
            assign_contractor(row['contractor_codes'],
                row['target_row'] if row['status'] == 'Target'
                else row['reserve_row'] if row['status'] == 'Reserve'
                else row['other_row'])
            for _, row in group.iterrows()
        ]

        group['target_count'] = group[group['status'] == 'Target'].groupby('assigned_contractor').cumcount() + 1
        group['reserve_count'] = group[group['status'] == 'Reserve'].groupby('assigned_contractor').cumcount() + 1

        group['assigned_contractor'] = group.apply(
            lambda x: "Not Assigned" if
            (x['status'] == 'Target' and x.get('target_count', 0) > 6) or
            (x['status'] == 'Reserve' and x.get('reserve_count', 0) > 3)
            else x['assigned_contractor'],
            axis=1
        )

        return group

    final_df = merged_df.groupby(['villageidentifier', 'DAY'], group_keys=False).apply(process_group)

    # Drop helper columns
    cleaned_df = final_df.drop(columns=[
        'contractor_codes', 'priority', 'target_row', 'reserve_row', 'other_row',
        'target_count', 'reserve_count', 'villageidentifier'
    ])

    # ✅ Show final results
    st.success("✅ Contractor Assignment Complete!")
    st.subheader("📋 Final Assigned Cases")
    st.dataframe(cleaned_df)

    # 🔎 Show mismatch summaries
    missing_clusters = (
        merged_df[merged_df['Contractors Code'].isna()]
        .groupby(['district', 'cluster'])
        .size()
        .reset_index(name='missing_count')
    )

    missing_villages = (
        merged_df[merged_df['Contractors Code'].isna()]
        .groupby(['district', 'cluster', 'village'])
        .size()
        .reset_index(name='missing_count')
    )

    st.subheader("📍 Clusters Missing Contractor Codes")
    st.dataframe(missing_clusters)

    st.subheader("🏘️ Villages Missing Contractor Codes")
    st.dataframe(missing_villages)
