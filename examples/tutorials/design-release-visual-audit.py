from __future__ import annotations
from _shared import *
d=demo(900).rename(columns={'participant_id':'participant','MEDIA_ID':'trial','interface_complexity':'condition'})
audit=gp.audit_gazepoint_experiment_design(d,participant_col='participant',trial_col='trial',condition_col='condition')
fig=gp.plot_gazepoint_design_coverage(audit); finish('design-release-visual-audit',audit=audit,figure=fig)
