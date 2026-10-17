from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Smart Daily Shift & Absence Manager", layout="centered"
)

st.title("🛠️ Smart Daily Shift & Absence Manager")
st.write(
    "Enter the date to calculate the schedule and track absent coverages."
)

# Team Names Mapping Table inside Sidebar
st.sidebar.markdown("### 👥 Team Members Reference")
team_data = {
    "Role": ["M1", "M2", "M3", "M4", "M5", "E1", "E2", "E3", "E4", "E5"],
    "Name": [
        "Anthony",
        "Hamed",
        "Tony",
        "Jimmy",
        "Maleek",
        "Darrison",
        "Daniel",
        "Jon",
        "Trey",
        "Ronald",
    ],
}
df_team = pd.DataFrame(team_data)
st.sidebar.table(df_team)


# Function to calculate cycle day
def get_day_number_from_date(target_date):
  base_date = datetime(2026, 9, 28)
  cycle_pattern = [0, 1, 4, 5, 6, 9, 10]
  days_diff = (target_date - base_date).days

  if days_diff < 0:
    return None, "Date is before the schedule start date (Sept 28, 2026)."

  weeks_passed = days_diff // 14
  remainder_days = days_diff % 14

  matching_day_in_cycle = -1
  for idx, offset in enumerate(cycle_pattern):
    if remainder_days == offset:
      matching_day_in_cycle = idx + 1
      break

  if matching_day_in_cycle != -1:
    day_num = (weeks_passed * 7) + matching_day_in_cycle
    return day_num, None
  else:
    return (
        None,
        "This date falls on a weekend/off-day in your custom shift pattern.",
    )


# Date input fields on the web UI
col1, col2, col3 = st.columns(3)
with col1:
  year = st.number_input("Year", value=2026, min_value=2026, max_value=2030)
with col2:
  month = st.number_input("Month", value=9, min_value=1, max_value=12)
with col3:
  day_of_month = st.number_input(
      "Day of Month", value=28, min_value=1, max_value=31
  )

try:
  target_date = datetime(int(year), int(month), int(day_of_month))
except ValueError:
  st.error("Invalid date entered!")
  st.stop()

day, error_msg = get_day_number_from_date(target_date)

if error_msg:
  st.error(error_msg)
  st.stop()

date_str = target_date.strftime("%A %m/%d/%Y")
st.success(f"**Target Date:** {date_str} evaluated to **[ Day {day} ]**")

# Absence section
has_absence = st.radio("Is there any absence today?", ("No", "Yes"))

all_mechanics = [f"M{i}" for i in range(1, 6)]
all_electricians = [f"E{i}" for i in range(1, 6)]
all_people = all_mechanics + all_electricians

absent_person = None
if has_absence == "Yes":
  absent_person = st.selectbox("Select the absent person:", all_people)

round_times = {
    "R1": "6am-8am",
    "R2": "8am-10am",
    "R3": "10am-12pm",
    "R4": "12pm-2pm",
    "R5": "2pm-4pm",
    "R6": "4pm-6pm",
}

# Generate Schedule button
if st.button("Generate Schedule"):
  base_r_entries = {}
  for r in range(1, 7):
    m_idx = (r - 1 + (day - 1)) % 5
    e_offset = 0 if r <= 5 else 1
    e_idx = (r - 1 + (day - 1) + e_offset) % 5
    col_name = f"R{r} ({round_times[f'R{r}']})"
    base_r_entries[col_name] = f"{all_mechanics[m_idx]}-{all_electricians[e_idx]}"

  report_messages = []

  def get_person_shift_count(person, current_schedule):
    count = 0
    for r_k, p_str in current_schedule.items():
      p1, p2 = p_str.split("-")
      if person == p1 or person == p2:
        count += 1
    return count

  r_keys = list(base_r_entries.keys())
  modified_r_entries = base_r_entries.copy()

  if has_absence == "No":
    report_messages.append("No one is absent today. The schedule runs normally.")
  else:
    is_mechanic_absent = absent_person in all_mechanics
    if is_mechanic_absent:
      same_category_pool = all_mechanics
      other_category_pool = all_electricians
    else:
      same_category_pool = all_electricians
      other_category_pool = all_mechanics

    report_messages.append(f"Today, **{absent_person}** is absent.")

    # STEP 1: Fix regular rounds allowing MM, EE, or ME flexible pairs with max 2 shifts per person limit
    for i, r_key in enumerate(r_keys):
      pair_str = modified_r_entries[r_key]
      p1, p2 = pair_str.split("-")

      if absent_person == p1 or absent_person == p2:
        other_person = p2 if absent_person == p1 else p1

        strict_busy = {other_person}
        if i > 0:
          prev_p1, prev_p2 = modified_r_entries[r_keys[i - 1]].split("-")
          strict_busy.update([prev_p1, prev_p2])
        if i < len(r_keys) - 1:
          next_p1, next_p2 = base_r_entries[r_keys[i + 1]].split("-")
          strict_busy.update([next_p1, next_p2])

        def get_candidates(pool):
          return [
              p for p in pool
              if p not in strict_busy 
              and p != absent_person 
              and p != other_person
              and get_person_shift_count(p, modified_r_entries) < 2  # Hard limit: max 2 shifts per day
          ]

        valid_candidates = get_candidates(same_category_pool)
        if not valid_candidates:
          valid_candidates = get_candidates(other_category_pool)

        if not valid_candidates:
          fallback_busy = {other_person, absent_person}
          valid_candidates = [
              p for p in same_category_pool 
              if p not in fallback_busy and get_person_shift_count(p, modified_r_entries) < 2
          ]
          if not valid_candidates:
            valid_candidates = [
                p for p in other_category_pool 
                if p not in fallback_busy and get_person_shift_count(p, modified_r_entries) < 2
            ]

        if not valid_candidates:
          valid_candidates = [p for p in all_people if p != absent_person and p != other_person]

        replacement = min(
            valid_candidates,
            key=lambda p: (get_person_shift_count(p, modified_r_entries), p),
        )

        if absent_person == p1:
          new_pair = f"{replacement}-{other_person}"
        else:
          new_pair = f"{other_person}-{replacement}"

        modified_r_entries[r_key] = new_pair
        report_messages.append(
            f"- In **{r_key}**, **{replacement}** replaced the absent person (flexible pair)."
        )

  # STEP 2: Build New Simultaneous Round (Concurrent with R1: 6am-8am)
  # Must not be in R1 and must not be in R2 (8am-10am), max 2 shifts per day limit
  r1_key = r_keys[0] # R1
  r2_key = r_keys[1] # R2
  r1_workers = modified_r_entries[r1_key].split("-")
  r2_workers = modified_r_entries[r2_key].split("-")

  excluded_for_new_round = set(r1_workers + r2_workers)
  if has_absence == "Yes" and absent_person:
    excluded_for_new_round.add(absent_person)

  available_for_new = [
      p for p in all_people 
      if p not in excluded_for_new_round 
      and get_person_shift_count(p, modified_r_entries) < 2
  ]

  # Pick 2 people for the new 6am-8am round (e.g. 1 mechanic, 1 electrician if possible, sorted by least load)
  avail_m_new = sorted(
      [p for p in available_for_new if p in all_mechanics],
      key=lambda p: (get_person_shift_count(p, modified_r_entries), p)
  )
  avail_e_new = sorted(
      [p for p in available_for_new if p in all_electricians],
      key=lambda p: (get_person_shift_count(p, modified_r_entries), p)
  )

  new_member1 = avail_m_new[0] if avail_m_new else (avail_e_new[0] if avail_e_new else "M1")
  # Try to pick second member from different category or next best
  remaining_avail = [p for p in available_for_new if p != new_member1]
  new_member2 = remaining_avail[0] if remaining_avail else "E1"

  new_round_str = f"{new_member1}-{new_member2}"

  # Construct final display data
  schedule_data = {
      "Day": [f"Day {day}"],
      "Date": [date_str],
      "Absent Person": [absent_person if has_absence == "Yes" else "None"],
      "Simultaneous R1 (6am-8am)": [new_round_str],
      **{k: [v] for k, v in modified_r_entries.items()},
  }

  df = pd.DataFrame(schedule_data)

  st.subheader("Resulting Schedule:")
  st.dataframe(df)

  st.markdown("### 📝 Shift & Absence Report:")
  for msg in report_messages:
    st.info(msg)
