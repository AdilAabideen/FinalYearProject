from typing import Any, Dict, List, Optional
import json
from pydantic import BaseModel, Field
from app.api.endpoints.medrecon import get_medrecons_by_subject
from app.neo4j_db import get_neo4j_driver
from datetime import datetime

from langchain.tools import tool

class GetVitalsConfoundersInput(BaseModel):
    subject_id: int = Field(description="The subject ID of the patient")
    in_time: datetime = Field(description="The time in which the vital signs were taken")

@tool("get_vitals_confounders", args_schema=GetVitalsConfoundersInput)
def get_vitals_confounders(
    subject_id: int,
    in_time: datetime
) -> Dict[str, Any]:
    """

    Given a Subject Id ( The Patient ) and Intime ( the Time Patients Vitals Signs were Taken ) this tool will return a List of Confounders. 
    Confounders are conditions that can distort how Vital Signs are Interpreted and they Arise from Medications that the Patient is on.
    Confounders are a list of objects that have the following properties:
    - confounder_name -> The Name of the Confounder
    - mechanism -> The Mechanism of the Confounder
    - direction -> The Direction of the Confounder
    - reliability -> The Reliability of the Confounder
    - use_rule -> The Rule to use when making a Decision on the Confounder
    You Should always Call this Tool when you are making a Decision on the Vital Signs of a Patient to Check for any infromation According to the Vitals
    THIS IS A VERY IMPORTANT TOOL AND THE RETURN SHOULD BE USED AS CONTEXT TO MAKE A DECISION

    Return : 
    - ok: True if the Confounders are found successfully
    - confounders: List of Confounder Objects
    - Medication Evidence: The Medications that the Patient is currenlty on, Medications can affect Vital Signs
    - Confounder Summary: A Summary of the Confounders that the Patient is on due to the Medications they are taking

    Eg:
    Input: subject_id = 123, in_time = [datetime(2026, 1, 1, 12, 0, 0)]
    Output: {"ok": True, "confounders": [{"confounder_name": "Confounder 1", "mechanism": "Mechanism 1", "direction": "Direction 1", "reliability": "Reliability 1", "use_rule": "Use Rule 1"}], "Medication Evidence": "The Patient is on Medication 1 and Medication 2", "Confounder Summary": "The Patient has Confounder 1 and Confounder 2"}
    """


    medrecons = get_medrecons_by_subject(
        subject_id=subject_id,
        charttime_start=None,
        charttime_end=in_time,
        limit=1000,
        offset=0,
        order="asc",
        db=__import__("app.database", fromlist=["SessionLocal"]).SessionLocal(),
    )

    etccodes = list(dict.fromkeys([medrecon.etccode for medrecon in medrecons if medrecon.etccode is not None]))

    if not etccodes:
        record = None
    else:
        cypher = """
        WITH [code IN $etccodes WHERE code IS NOT NULL | toFloat(code)] AS codes
        MATCH (c:ETCCategories)
        WHERE c.etccode IN codes
        OPTIONAL MATCH (c)-[r:CanAffect]->(conf:Confounders)
        WITH c, r, conf
        WHERE conf IS NOT NULL
        RETURN
          collect(DISTINCT {
            confounder_name: conf.confounder_name,
            mechanism: r.mechanism,
            direction: r.direction,
            reliability: r.reliability,
            use_rule: r.use_rule
          }) AS confounders,
          collect(DISTINCT {
            etccode: c.etccode,
            etcdescription: coalesce(c.etcdescription, "")
          }) AS evidence
        """

        driver = get_neo4j_driver()
        with driver.session() as session:
            record = session.run(cypher, etccodes=etccodes).single()

    confounders = record["confounders"] if record else []
    evidence_from_graph = record["evidence"] if record else []


    if evidence_from_graph:
        evidence = "The Use Uses Medications in the Following Categories: \n"
        for e in evidence_from_graph:
            evidence += f" - {e['etcdescription']}\n"
    else:
        evidence = "This Patient is not on any Medications"
    
    if confounders:
      confounder_summary = "This Can Lead to these Confounders Which Can distort how Vital Signals can be Interpreted : \n"
      for c in confounders:
        confounder_summary += f""" - Confounder Name : {c['confounder_name']} \n 
          - Which Has a Direction that is {c['direction']} \n 
          - And a Mechanism that is {c['mechanism']} \n 
          - And a Reliability of {c['reliability']} \n 
          - Make sure to use this Rule aswell which should be taken with high priority when making a Decision of the confounder and the Vital Signs {c['use_rule']} \n 
          .\n"""
      confounder_summary += "Make sure to use this information to make a decision on the Confounders and the Vital Signs"
    else:
      confounder_summary = "No Confounders Affected the Vital Signs of this Patient Can be Found"

    return {
        "ok": True,
        "confounders": confounders,
        "Medication Evidence": evidence,
        "Confounder Summary": confounder_summary
    }
