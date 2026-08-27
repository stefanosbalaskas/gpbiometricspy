from __future__ import annotations
from _shared import *
d=demo(900).rename(columns={'participant_id':'participant','MEDIA_ID':'trial','interface_complexity':'condition'})
design=gp.audit_gazepoint_experiment_design(d,participant_col='participant',trial_col='trial',condition_col='condition')
balance=gp.audit_gazepoint_condition_balance(d,participant_col='participant',condition_col='condition',trial_col='trial')
events=gp.audit_gazepoint_event_coverage(d,event_col='TTL0',participant_col='participant',trial_col='trial'); finish('design-audit-workflow',design=design,balance=balance,events=events)
