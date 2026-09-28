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

default_special_members_list = [
    ["M2", "M3", "E1", "E3"],  # Day 1
    ["M3", "M4", "E2", "E4"],  # Day 2
    ["M4", "M5", "E3", "E5"],  # Day 3
    ["M1", "M5", "E1", "E4"],  # Day 4
    ["M1", "M2", "E2", "E5"],  # Day 5
    ["M2", "M3", "E1", "E3"],  # Day 6
    ["M3", "M4", "E2", "E4"],  # Day 7
]

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

  if has_absence == "No":
    default_special = default_special_members_list[
        (day - 1) % len(default_special_members_list)
    ]
    special_str = ", ".join(default_special)

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

    is_mechanic_absent = absent_person in all_mechanics
    if is_mechanic_absent:
      primary_pool_base = [m for m in all_mechanics if m != absent_person]
      secondary_pool_base = list(all_electricians)
    else:
      primary_pool_base = [e for e in all_electricians if e != absent_person]
      secondary_pool_base = list(all_mechanics)

    report_messages.append(f"Today, **{absent_person}** is absent.")

    # Helper function to count how many shifts a person currently has in modified_r_entries
    def get_person_shift_count(person, current_schedule):
      count = 0
      for r_k, p_str in current_schedule.items():
        p1, p2 = p_str.split("-")
        if person == p1 or person == p2:
          count += 1
      return count

    # STEP 1: Fix regular rounds with strict constraints and least-load priority
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

        def get_strict_candidates(pool):
          return [p for p in pool if p not in strict_busy and p != absent_person]

        valid_candidates = get_strict_candidates(primary_pool_base)
        if not valid_candidates:
          valid_candidates = get_strict_candidates(secondary_pool_base)

        if not valid_candidates:
          valid_candidates = [p for p in primary_pool_base if p != other_person and p != absent_person]
          if not valid_candidates:
            valid_candidates = [p for p in secondary_pool_base if p != other_person and p != absent_person]

        # Select the candidate who has the LOWEST number of shifts so far today (Least-load priority)
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
            f"- In **{r_key}**, **{replacement}** replaced the absent person."
        )

    # STEP 2: Build Special Round dynamically from remaining available people
    r5_key = [k for k in r_keys if "R5" in k][0]
    r5_workers = modified_r_entries[r5_key].split("-")

    available_for_special = [
        p for p in all_people if p not in r5_workers and p != absent_person
    ]

    avail_m = [p for p in available_for_special if p in all_mechanics]
    avail_e = [p for p in available_for_special if p in all_electricians]

    r4_key = [k for k in r_keys if "R4" in k][0]
    r6_key = [k for k in r_keys if "R6" in k][0]
    r4_workers = modified_r_entries[r4_key].split("-")
    r6_workers = modified_r_entries[r6_key].split("-")

    def pick_special(pool, count):
      perfect = [
          p for p in pool if p not in r4_workers and p not in r6_workers
      ]
      fallback = [p for p in pool if p not in perfect]
      combined = perfect + fallback
      # Sort by shift count (least-load) then role name
      combined_sorted = sorted(
          combined,
          key=lambda p: (get_person_shift_count(p, modified_r_entries), p),
      )
      return combined_sorted[:count]

    chosen_m = pick_special(avail_m, 2)
    chosen_e = pick_special(avail_e, 2)

    if len(chosen_m) < 2:
      extra_m = [
          p
          for p in all_mechanics
          if p not in chosen_m
          and p not in r5_workers
          and p != absent_person
      ]
      chosen_m += extra_m[: 2 - len(chosen_m)]
    if len(chosen_e) < 2:
      extra_e = [
          p
          for p in all_electricians
          if p not in chosen_e
          and p not in r5_workers
          and p != absent_person
      ]
      chosen_e += extra_e[: 2 - len(chosen_e)]

    chosen_special = sorted(chosen_m) + sorted(chosen_e)
    special_str = ", ".join(chosen_special)

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
