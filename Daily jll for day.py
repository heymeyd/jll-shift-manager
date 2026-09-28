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
  # 1. Calculate base and standard daily schedule
  base_r_entries = {}
  for r in range(1, 7):
    m_idx = (r - 1 + (day - 1)) % 5
    e_offset = 0 if r <= 5 else 1
    e_idx = (r - 1 + (day - 1) + e_offset) % 5
    col_name = f"R{r} ({round_times[f'R{r}']})"
    base_r_entries[col_name] = f"{all_mechanics[m_idx]}-{all_electricians[e_idx]}"

  special_round_patterns = [
      "M2, M3 & E1, E3",
      "M3, M4 & E2, E4",
      "M4, M5 & E3, E5",
      "M1, M5 & E1, E4",
      "M1, M2 & E2, E5",
  ]
  special_str = special_round_patterns[(day - 1) % 5]

  report_messages = []

  if has_absence == "No":
    schedule_data = {
        "Day": [f"Day {day}"],
        "Date": [date_str],
        "Absent Person": ["None"],
        **{k: [v] for k, v in base_r_entries.items()},
        "Special R5 (2pm-4pm)": [special_str],
    }
    report_messages.append(
        "No one is absent today. The schedule runs normally."
    )
  else:
    r_keys = list(base_r_entries.keys())
    modified_r_entries = base_r_entries.copy()
    all_active_pool = [p for p in all_people if p != absent_person]

    report_messages.append(f"Today, **{absent_person}** is absent.")

    for i, r_key in enumerate(r_keys):
      pair_str = base_r_entries[r_key]
      p1, p2 = pair_str.split("-")

      if absent_person == p1 or absent_person == p2:
        other_person = p2 if absent_person == p1 else p1

        busy_people = {other_person}
        if i > 0:
          prev_p1, prev_p2 = base_r_entries[r_keys[i - 1]].split("-")
          busy_people.update([prev_p1, prev_p2])
        if i < len(r_keys) - 1:
          next_p1, next_p2 = base_r_entries[r_keys[i + 1]].split("-")
          busy_people.update([next_p1, next_p2])

        ideal_candidates = [
            p for p in all_active_pool if p not in busy_people
        ]

        if not ideal_candidates:
          fallback_candidates = [
              p
              for p in all_active_pool
              if p != other_person
              and p not in base_r_entries[r_key].split("-")
          ]
          ideal_candidates = (
              fallback_candidates if fallback_candidates else all_active_pool
          )

        replacement = ideal_candidates[
            (
                hash(r_key)
                + day
                + (
                    1
                    if absent_person in all_mechanics
                    else len(all_mechanics)
                )
            )
            % len(ideal_candidates)
        ]

        if absent_person == p1:
          new_pair = f"{replacement}-{other_person}"
        else:
          new_pair = f"{other_person}-{replacement}"

        modified_r_entries[r_key] = new_pair
        report_messages.append(
            f"- In **{r_key}**, **{replacement}** replaced the absent person."
        )

    schedule_data = {
        "Day": [f"Day {day}"],
        "Date": [date_str],
        "Absent Person": [absent_person],
        **{k: [v] for k, v in modified_r_entries.items()},
        "Special R5 (2pm-4pm)": [special_str],
    }

  df = pd.DataFrame(schedule_data)

  st.subheader("Resulting Schedule:")
  st.dataframe(df)

  st.markdown("### 📝 Shift & Absence Report:")
  for msg in report_messages:
    st.info(msg)
