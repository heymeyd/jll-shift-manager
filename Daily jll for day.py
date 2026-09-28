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

# Base default special round members for fallback pattern display
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
  # 1. Calculate base and standard daily schedule
  base_r_entries = {}
  for r in range(1, 7):
    m_idx = (r - 1 + (day - 1)) % 5
    e_offset = 0 if r <= 5 else 1
    e_idx = (r - 1 + (day - 1) + e_offset) % 5
    col_name = f"R{r} ({round_times[f'R{r}']})"
    base_r_entries[col_name] = f"{all_mechanics[m_idx]}-{all_electricians[e_idx]}"

  report_messages = []

  if has_absence == "No":
    # Normal day schedule
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

    # STEP 1: Fix regular rounds with strict constraints (No same shift, no before, no after)
    for i, r_key in enumerate(r_keys):
      pair_str = modified_r_entries[r_key]
      p1, p2 = pair_str.split("-")

      if absent_person == p1 or absent_person == p2:
        other_person = p2 if absent_person == p1 else p1

        # Strict busy people for regular rounds: other person + adjacent shifts (before and after)
        strict_busy = {other_person}
        if i > 0:
          prev_p1, prev_p2 = modified_r_entries[r_keys[i - 1]].split("-")
          strict_busy.update([prev_p1, prev_p2])
        if i < len(r_keys) - 1:
          next_p1, next_p2 = base_r_entries[r_keys[i + 1]].split("-")
          strict_busy.update([next_p1, next_p2])

        def get_strict_candidates(pool):
          return [p for p in pool if p not in strict_busy]

        # Priority 1: Primary category pool with strict no-adjacent rule
        valid_candidates = get_strict_candidates(primary_pool_base)

        # Priority 2: Secondary category pool with strict no-adjacent rule
        if not valid_candidates:
          valid_candidates = get_strict_candidates(secondary_pool_base)

        # Fallback if no one found without adjacent shifts
        if not valid_candidates:
          valid_candidates = [p for p in primary_pool_base if p != other_person]
          if not valid_candidates:
            valid_candidates = [p for p in secondary_pool_base if p != other_person]

        replacement = valid_candidates[
            (
                hash(r_key)
                + day
                + (1 if is_mechanic_absent else len(all_mechanics))
            )
            % len(valid_candidates)
        ]

        if absent_person == p1:
          new_pair = f"{replacement}-{other_person}"
        else:
          new_pair = f"{other_person}-{replacement}"

        modified_r_entries[r_key] = new_pair
        report_messages.append(
            f"- In **{r_key}**, **{replacement}** replaced the absent person."
        )

    # STEP 2: Build Special Round dynamically from remaining available people after regular shifts are set
    # Get all people working in R5 (2pm-4pm) from modified regular schedule
    r5_key = [k for k in r_keys if "R5" in k][0]
    r5_workers = modified_r_entries[r5_key].split("-")

    # People available for special round: anyone not working in R5 regular shift and not absent
    available_for_special = [
        p for p in all_people if p not in r5_workers and p != absent_person
    ]

    # Sub-divide into mechanics and electricians for balanced special round selection
    avail_m = [p for p in available_for_special if p in all_mechanics]
    avail_e = [p for p in available_for_special if p in all_electricians]

    # Select 2 mechanics and 2 electricians preferentially who are not in R4 or R6 (adjacent to R5)
    def pick_special(pool, count, r4_workers, r6_workers):
      # Priority 1: Not in R4 and not in R6
      perfect = [
          p for p in pool if p not in r4_workers and p not in r6_workers
      ]
      # Priority 2: Allowed to be in R4 or R6 if needed
      fallback = [p for p in pool if p not in perfect]
      combined = perfect + fallback
      return combined[:count]

    r4_key = [k for k in r_keys if "R4" in k][0]
    r6_key = [k for k in r_keys if "R6" in k][0]
    r4_workers = modified_r_entries[r4_key].split("-")
    r6_workers = modified_r_entries[r6_key].split("-")

    chosen_m = pick_special(avail_m, 2, r4_workers, r6_workers)
    chosen_e = pick_special(avail_e, 2, r4_workers, r6_workers)

    # If we lack members due to strict counts, pull from general available pool
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
