from __future__ import annotations
from _shared import *
d=demo(300); log=gp.create_gazepoint_analysis_decision_log(study_id='tutorial',analyst='example'); methods=gp.create_gazepoint_biometrics_methods_text(data=d); repro=gp.create_gazepoint_reproducibility_statement(decision_log={'decisions':log},package_version=gp.__version__)
with tempfile.TemporaryDirectory() as td: bundle=gp.export_gazepoint_biometrics_report_bundle(output_dir=td,prefix='tutorial',tables={'sample':d.head(10)},text={'methods':methods,'reproducibility':repro},overwrite=True)
finish('reporting-reproducibility-workflow',decision_log=log,bundle=bundle)
