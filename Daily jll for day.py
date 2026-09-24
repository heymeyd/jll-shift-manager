from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Smart Daily Shift Manager", layout="centered"
)

st.title("🛠️ Smart Daily Shift & Absence Manager")
st.write(
    "Enter the date to automatically calculate the cycle day and schedule."
)


# تابع محاسبه روز چرخه (دقیقاً همون منطق خودتون)
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


# فیلدهای ورودی تاریخ در وب
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

# سوالات غیبت و راند ویژه
has_absence = st.radio("1. Is there any absence today?", ("No", "Yes"))

all_mechanics = [f"M{i}" for i in range(1, 6)]
all_electricians = [f"E{i}" for i in range(1, 6)]
all_people = all_mechanics + all_electricians

absent_person = None
has_special = "No"

if has_absence == "Yes":
  absent_person = st.selectbox("2. Select the absent person:", all_people)
  has_special_choice = st.radio(
      f"3. Despite {absent_person}'s absence, is there a special round today?",
      ("Yes", "No"),
  )
  has_special = has_special_choice

round_times = {
    "R1": "6am-8am",
    "R2": "8am-10am",
    "R3": "10am-12pm",
    "R4": "12pm-2pm",
    "R5": "2pm-4pm",
    "R6": "4pm-6pm",
}

# دکمه تولید برنامه
if st.button("Generate Schedule"):
  if has_absence == "No":
    r_entries = {}
    for r in range(1, 7):
      m_idx = (r - 1 + (day - 1)) % 5
      e_offset = 0 if r <= 5 else 1
      e_idx = (r - 1 + (day - 1) + e_offset) % 5
      col_name = f"R{r} ({round_times[f'R{r}']})"
      r_entries[col_name] = f"{all_mechanics[m_idx]}-{all_electricians[e_idx]}"

    special_round_patterns = [
        "M2, M3 & E1, E3",
        "M3, M4 & E2, E4",
        "M4, M5 & E3, E5",
        "M1, M5 & E1, E4",
        "M1, M2 & E2, E5",
    ]
    special_str = special_round_patterns[(day - 1) % 5]

    schedule_data = {
        "Day": [f"Day {day}"],
        "Date": [date_str],
        "Absent Person": ["None"],
        **{k: [v] for k, v in r_entries.items()},
        "Special R5 (2pm-4pm)": [special_str],
    }
  else:
    if absent_person in all_mechanics:
      active_mechs = [m for m in all_mechanics if m != absent_person]
      active_elecs = list(all_electricians)
    else:
      active_mechs = list(all_mechanics)
      active_elecs = [e for e in all_electricians if e != absent_person]

    all_active_pool = active_mechs + active_elecs

    if has_special == "Yes":
      m_idx1 = (day - 1) % len(active_mechs)
      m_idx2 = day % len(active_mechs)
      spec_mechs = [active_mechs[m_idx1], active_mechs[m_idx2]]

      e_idx1 = (day - 1) % len(active_elecs)
      e_idx2 = day % len(active_elecs)
      spec_elecs = [active_elecs[e_idx1], active_elecs[e_idx2]]

      special_str = (
          f"{spec_mechs[0]}, {spec_mechs[1]} & {spec_elecs[0]},"
          f" {spec_elecs[1]}"
      )
      special_group = set(spec_mechs + spec_elecs)

      r_entries = {}
      daily_assigned = set()
      for r in range(1, 7):
        if r >= 4:
          allowed_pool = [
              p
              for p in all_active_pool
              if p not in special_group and p not in daily_assigned
          ]
        else:
          allowed_pool = [p for p in all_active_pool if p not in daily_assigned]

        if len(allowed_pool) < 2:
          allowed_pool = [p for p in all_active_pool if p not in daily_assigned]
        if len(allowed_pool) < 2:
          allowed_pool = list(all_active_pool)
          daily_assigned.clear()

        idx1 = (r * 3 + day) % len(allowed_pool)
        p1 = allowed_pool[idx1]
        temp_pool = [p for p in allowed_pool if p != p1]
        idx2 = (r + day * 2) % len(temp_pool)
        p2 = temp_pool[idx2]

        col_name = f"R{r} ({round_times[f'R{r}']})"
        r_entries[col_name] = f"{p1}-{p2}"
        daily_assigned.clear()
        daily_assigned.add(p1)
        daily_assigned.add(p2)

      schedule_data = {
          "Day": [f"Day {day}"],
          "Date": [date_str],
          "Absent Person": [absent_person],
          **{k: [v] for k, v in r_entries.items()},
          "Special R5 (2pm-4pm)": [special_str],
      }
    else:
      r_entries = {}
      previous_round_workers = set()
      for r in range(1, 7):
        available_pool = [
            p for p in all_active_pool if p not in previous_round_workers
        ]
        if len(available_pool) < 2:
          available_pool = list(all_active_pool)

        idx1 = (r * 3 + day) % len(available_pool)
        p1 = available_pool[idx1]
        temp_pool = [p for p in available_pool if p != p1]
        idx2 = (r + day * 7) % len(temp_pool)
        p2 = temp_pool[idx2]

        col_name = f"R{r} ({round_times[f'R{r}']})"
        r_entries[col_name] = f"{p1}-{p2}"
        previous_round_workers = {p1, p2}

      schedule_data = {
          "Day": [f"Day {day}"],
          "Date": [date_str],
          "Absent Person": [absent_person],
          **{k: [v] for k, v in r_entries.items()},
      }

  df = pd.DataFrame(schedule_data)
  st.subheader("Resulting Schedule:")
  st.dataframe(df)