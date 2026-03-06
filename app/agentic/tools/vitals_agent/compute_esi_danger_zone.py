from langchain.tools import tool
from pydantic import BaseModel, Field

class ESI_Danger_Zone_Vitals(BaseModel):
    age_years: float = Field(description="The age of the patient in years")
    hr: float  = Field(description="The heart rate of the patient in beats per minute")
    rr: float  = Field(description="The respiratory rate of the patient in breaths per minute")
    spo2: float  = Field(description="The oxygen saturation of the patient in percentage")
    has_respiratory_compromise: bool = Field(description="Whether the patient has respiratory compromise By Looking at the Cheif Complaint")

@tool("Compute ESI Danger Zone", args_schema=ESI_Danger_Zone_Vitals)
def compute_esi_danger_zone(
    input: ESI_Danger_Zone_Vitals
) -> dict:
    """
    Implements the ESI Danger Zone Calculation. This is the Best tool and Most important tool to see if there should be an uptriage. 
    It is a simple tool that takes in the vital signs and returns the ESI Danger Zone Status.

    Args:
        input: ESI_Danger_Zone_Vitals -> The Vitals and if the Patient has respiratory compromise and their Age

    Returns:
        Dict 
            - ok: True if the ESI Danger Zone Status is calculated successfully
            - age_band: The age band of the patient
            - thresholds: The thresholds for the vital signs in the form of a dictionary with the keys 'hr_gt', 'rr_gt', and 'spo2_lt_when_respiratory_compromise'
            - status: The status of the ESI Danger Zone
            - context: The context of the ESI Danger Zone This is what you should use the msot to determine the next steps and actions to take.
            - violations: The violations of the ESI Danger Zone in the form of a dictionary with the keys 'red' and 'orange' which are the different levels of Violations
    """
    # Convert age_years into the band used by ESI
    age_years = input.age_years
    hr = input.hr
    rr = input.rr
    spo2 = input.spo2
    has_respiratory_compromise = input.has_respiratory_compromise

    if age_years < (1 / 12):  # < 1 month
        hr_thr, rr_thr = 190.0, 60.0
        age_band = "<1_month"
    elif age_years < 1:  # 1-12 months
        hr_thr, rr_thr = 180.0, 55.0
        age_band = "1_12_months"
    elif age_years < 3:  # 1-3 years
        hr_thr, rr_thr = 140.0, 40.0
        age_band = "1_3_years"
    elif age_years < 5:  # 3-5 years
        hr_thr, rr_thr = 120.0, 35.0
        age_band = "3_5_years"
    elif age_years < 12:  # 5-12 years
        hr_thr, rr_thr = 120.0, 30.0
        age_band = "5_12_years"
    elif age_years < 18:  # 12-18 years
        hr_thr, rr_thr = 100.0, 20.0
        age_band = "12_18_years"
    else:  # >18 years
        hr_thr, rr_thr = 100.0, 20.0
        age_band = "adult"

    OVERBAND_PCT = 0.05
    OVERBAND_PCT_SPO2 = 0.01
    SPO2_THR = 92.0

    orange_reasons = []
    red_reasons = []
    missing_vitals = []

    def classify_upper(vital_name: str, value: float | None, threshold: float):
        if value is None:
            missing_vitals.append(vital_name)
            return

        orange_upper = threshold * (1 + OVERBAND_PCT)
        if value > threshold:
            if value <= orange_upper:
                orange_reasons.append(
                    f"{vital_name}>{threshold:.1f} but <= {orange_upper:.1f} (5% overband, age_band={age_band}) Hence this is in the Soft Danger Zone. Reference with Additional Vitals and History to Determine if this equates to Urgent Intervention"
                )
            else:
                red_reasons.append(
                    f"{vital_name}>{orange_upper:.1f} (>5% overband above {threshold:.1f}, age_band={age_band}) Hence this is in the Hard Danger Zone. Urgent Intervention Should be Highly Likely. Still Consider Additional Vitals and History to Determine if this equates to Urgent Intervention"
                )

    classify_upper("HR", hr, hr_thr)
    classify_upper("RR", rr, rr_thr)

    # SpO2 is evaluated only when potential respiratory compromise is present.
    if has_respiratory_compromise:
        if spo2 is None:
            missing_vitals.append("SpO2")
        else:
            orange_lower = SPO2_THR * (1 - OVERBAND_PCT_SPO2)
            if spo2 < SPO2_THR:
                if spo2 >= orange_lower:
                    orange_reasons.append(
                        f"SpO2<{SPO2_THR:.0f}% but >= {orange_lower:.1f}% (5% overband) with respiratory compromise Hence this is in the Soft Danger Zone. Reference with Additional Vitals and History to Determine if this equates to Urgent Intervention"
                    )
                else:
                    red_reasons.append(
                        f"SpO2<{orange_lower:.1f}% (>5% below {SPO2_THR:.0f}%) with respiratory compromise Hence this is in the Hard Danger Zone. Urgent Intervention Should be Highly Likely. Still Consider Additional Vitals and History to Determine if this equates to Urgent Intervention"
                    )

    high_risk = len(red_reasons) > 0
    orange_flag = len(orange_reasons) > 0

    if high_risk and orange_flag:
        status = "RED Flag Status"
        context = f"This Patient Vitals has violated multiple ESI Danger Zone Thresholds with {len(red_reasons)} Hard Danger Zone Violations such as {red_reasons} and {len(orange_reasons)} Soft Danger Zone Violations such as {orange_reasons}. Urgent Intervention Should be Highly Likely. Still Consider Additional Vitals and History to Determine if this equates to Urgent Intervention"
    if high_risk and not orange_flag:
        status = "RED Flag Status"
        context = f"This Patient Vitals has violated multiple ESI Danger Zone Thresholds with {len(red_reasons)} Hard Danger Zone Violations such as {red_reasons}. Urgent Intervention Should be Highly Likely. Still Consider Additional Vitals and History to Determine if this equates to Urgent Intervention"
    if not high_risk and len(orange_reasons) == 1 : 
        status = "ORANGE Flag Status"
        context = f"This Patient Vitals has violated A ESI Danger Zone Thresholds with {len(orange_reasons)} Soft Danger Zone Violations such as {orange_reasons}. There Could be a Change of Urgent Interventions howeve rwe should 100% Consult with Additionla information such as Medication and history to find this out "
    if not high_risk and orange_flag:
        status = "ORANGE Flag Status"
        context = f"This Patient Vitals has violated multiple ESI Danger Zone Thresholds with {len(orange_reasons)} Soft Danger Zone Violations such as {orange_reasons}. Urgent Intervention Should be Highly Likely however as it is in the Soft Danger Zone consult with Additional Information. Still Consider Additional Vitals and History to Determine if this equates to Urgent Intervention"
    if not high_risk and not orange_flag:
        status = "NONE Flag Status"
        context = f"This Patient Vitals has not violated any ESI Danger Zone Thresholds Urgent Intervention is not Likely however still consider additional information to find this out "


    return {
        "ok": True,
        "age_band": age_band,
        "thresholds": {
            "hr_gt": hr_thr,
            "rr_gt": rr_thr,
            "spo2_lt_when_respiratory_compromise": SPO2_THR,
        },
        "status": status,
        "context": context,
        "violations": {
            "red": red_reasons,
            "orange": orange_reasons,
        }
    }
