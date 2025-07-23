import pandas as pd
import streamlit as st

# Set up the app
st.set_page_config(page_title="AHS Contractor Assignment", layout="wide")
st.title("📊 AHS Contractor Assignment App")

# File uploaders
ahs_workplan_file = st.file_uploader("Upload AHS Workplan Excel", type=["xlsx"])
samxphilip_file = st.file_uploader("Upload SamXPhilip Excel", type=["xlsx"])

if ahs_workplan_file and samxphilip_file:
    AHS_workplan_Sam = pd.read_excel(ahs_workplan_file)
    SamXPhilip = pd.read_excel(samxphilip_file)

    # Create unique identifier
    SamXPhilip['villageidentifier'] = SamXPhilip['district'].str.title() + "_" + SamXPhilip['cluster'].str.title() + "_" + SamXPhilip['village'].str.title()
    AHS_workplan_Sam['villageidentifier'] = AHS_workplan_Sam['District'].str.title() + "_" + AHS_workplan_Sam['Cluster'].str.title() + "_" + AHS_workplan_Sam['Villages'].str.title()

    # Merge data
    merged_case_list_AHS = SamXPhilip.merge(
        AHS_workplan_Sam[['villageidentifier', 'DAY', 'DATE', 'Contractors Code']],
        on='villageidentifier',
        how='left'
    )

    # 🔍 Drop duplicated IDs before assigning
    merged_case_list_AHS.drop_duplicates(subset='id', keep='first',inplace=True)

    # Add logic columns
    merged_case_list_AHS['contractor_codes'] = merged_case_list_AHS['Contractors Code'].str.split(',')
    merged_case_list_AHS['priority'] = merged_case_list_AHS['status'].map({'Target': 1, 'Reserve': 2}).fillna(3)

    # Assignment logic
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

    final_result = merged_case_list_AHS.groupby(['villageidentifier', 'DAY'], group_keys=False).apply(process_group)

    # Drop helper columns
    cleaned_result = final_result.drop(columns=[
        'contractor_codes', 'priority', 'target_row', 'reserve_row', 'other_row',
        'target_count', 'reserve_count', 'villageidentifier'
    ])

    st.success("✅ Assignment complete. Here's the final data:")
    st.dataframe(cleaned_result)

    # Download assigned CSV
    csv = cleaned_result.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Assigned Contractor CSV", data=csv, file_name="Kisoro_assigned.csv", mime="text/csv")
