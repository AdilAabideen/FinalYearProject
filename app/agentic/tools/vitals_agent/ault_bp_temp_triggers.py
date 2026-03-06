from langchain.tools import tool
from pydantic import BaseModel, Field

class AdultBPTempTriggersInput(BaseModel):
    temp_f: float | None = Field(description="The temperature of the patient in Fahrenheit")
    sbp: float | None = Field(description="The systolic blood pressure of the patient in mmHg")
    dbp: float | None = Field(description="The diastolic blood pressure of the patient in mmHg")
    symptomatic_context: dict = Field(description="The symptomatic context of the patient in the form of a dictionary with the keys 'chest_pain', 'shortness_of_breath', 'neuro_deficit_or_confusion', 'pregnant_or_postpartum', and 'suspected_infection'")

@tool("Adult BP + Temp Triggers", args_schema=AdultBPTempTriggersInput)
def adult_bp_temp_triggers(
    input: AdultBPTempTriggersInput
) -> dict:
    """

    Minimal deterministic adult BP + Temp flags to support ESI-style reassessment.
    Use this tool at the start of the execution of the Agent. Interpret the Results and use the Context to determine the next steps and actions to take.
    This is a Simple Tool that takes in Blood Pressure and Temperature and returns some considitions that may mean that an Uptraige is Needed 
    Args:
        temp_f: The temperature of the patient in Fahrenheit
        sbp: The systolic blood pressure of the patient in mmHg
        dbp: The diastolic blood pressure of the patient in mmHg
        symptomatic_context: The symptomatic context of the patient in the form of a dictionary with the keys 'chest_pain', 'shortness_of_breath', 'neuro_deficit_or_confusion', 'pregnant_or_postpartum', and 'suspected_infection'
    Returns:
        Dict
            - hard_flags: The hard flags of the Adult BP + Temp Triggers
            - soft_flags: The soft flags of the Adult BP + Temp Triggers

    Hards Flags Can be considered for Uptriage however you should still look at Other Vitals and context such as medications and chief complaint before making the final decision.
    Soft Flags Can be considered for Uptriage but you HAVE TO still look at Other Vitals and context such as medications and chief complaint before making the final decision.
    Eg:
    Input: temp_f = 97.7, sbp = 120, dbp = 80, symptomatic_context = {'chest_pain': True, 'shortness_of_breath': True, 'neuro_deficit_or_confusion': True, 'pregnant_or_postpartum': False, 'suspected_infection': False}
    Output: {'hard_flags': ['AS SBP<=90 there is Hypotension Hence Uptriage is Likely You should still look at Other Vitals and context such as medications and chief complaint before making the final decision.'], 'soft_flags': ['As SBP 91-100 there is Borderline Hypotension Hence there is a chance of Uptriage but you should still look at Other Vitals and context such as medications and chief complaint before making the final decision.']}
    """
    temp_f = input.temp_f
    sbp = input.sbp
    dbp = input.dbp
    symptomatic_context = input.symptomatic_context

    reasons_hard, reasons_soft = [], []

    # --- BP (adult) ---
    if sbp is not None:
        if sbp <= 90:
            reasons_hard.append(" AS SBP<=90 there is Hypotension Hence Uptriage is Likely You should still look at Other Vitals and context such as medications and chief complaint before making the final decision.")
        elif 91 <= sbp <= 100:
            reasons_soft.append(" As SBP 91-100 there is Borderline Hypotension Hence there is a chance of Uptriage but you should still look at Other Vitals and context such as medications and chief complaint before making the final decision.")

        # Severe hypertension is only an emergency *with symptoms* (hypertensive emergency pattern)
        if sbp >= 180 and any(symptomatic_context.get(k, False) for k in
                             ["chest_pain","shortness_of_breath","neuro_deficit_or_confusion","pregnant_or_postpartum"]):
            reasons_hard.append("SBP>=180 with concerning symptoms Hence Uptriage is Likely You Should still look at Other Vitals and context such as medications and chief complaint before making the final decision.")

    if dbp is not None:
        if dbp >= 120 and any(symptomatic_context.get(k, False) for k in
                              ["chest_pain","shortness_of_breath","neuro_deficit_or_confusion","pregnant_or_postpartum"]):
            reasons_hard.append("DBP>=120 with concerning symptoms Hence Uptriage is Likely You Should still look at Other Vitals and context such as medications and chief complaint before making the final decision.")

    # --- Temperature (adult) ---
    # ESI gives pediatric temp red flags explicitly. For adults, use conservative bands to prompt reassessment,
    # and let complaint/history drive severity (like pneumonia/viral example with T 38.5 + RR 26 + SpO2 90). 
    # Temperature thresholds converted to Fahrenheit: 35.0°C = 95.0°F, 36.0°C = 96.8°F, 39.0°C = 102.2°F, 40.0°C = 104.0°F
    if temp_f is not None:
        if temp_f < 95.0:
            reasons_hard.append("Temp<95.0°F (significant hypothermia) Hence Uptraige is Likely You Should still look at Other Vitals and context such as medications and chief complaint before making the final decision.")
        elif temp_f < 96.8:
            reasons_soft.append("Temp 95.0-96.7°F (mild hypothermia) Hence there is a chance of Uptriage but you should still look at Other Vitals and context such as medications and chief complaint before making the final decision.")

        if temp_f >= 104.0:
            reasons_hard.append("Temp>=104.0°F (hyperpyrexia) Hence Uptriage is Likely You Should still look at Other Vitals and context such as medications and chief complaint before making the final decision.")
        elif temp_f >= 102.2:
            # fever alone isn't ESI-2; it becomes higher-risk with infection features or other abnormal vitals
            if symptomatic_context.get("suspected_infection", False):
                reasons_soft.append("Temp>=102.2°F with suspected infection Hence there is a chance of Uptriage but you should still look at Other Vitals and context such as medications and chief complaint before making the final decision.")
            else:
                reasons_soft.append("Temp>=102.2°F Hence there is a chance of Uptriage but you should still look at Other Vitals and context such as medications and chief complaint before making the final decision.")

    return {
        "hard_flags": reasons_hard,
        "soft_flags": reasons_soft
    }