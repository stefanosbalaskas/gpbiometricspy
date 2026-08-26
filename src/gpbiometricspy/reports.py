from __future__ import annotations

import math
import pandas as pd

from ._types import ReportText


def _scalar(value,name):
    if not isinstance(value,str) or not value.strip(): raise ValueError(f"`{name}` must be a non-empty scalar character value.")
    return value.strip()


def _logical(value,name):
    if not isinstance(value,bool): raise ValueError(f"`{name}` must be TRUE or FALSE.")
    return value


def _validate_named_validation(validation):
    if validation is None: return
    if not isinstance(validation,dict) or not validation or any(not str(k) for k in validation): raise ValueError("`validation` must be a named list.")


def _validate_audit(obj,name):
    if obj is None: return
    if not isinstance(obj,dict) or 'overview' not in obj: raise ValueError(f"`{name}` must be a gpbiometrics audit/profile object with an overview table.")
    if not isinstance(obj['overview'],pd.DataFrame): raise ValueError(f"`{name}` overview must be a data frame.")


def _validate_decision_log(log):
    if log is None: return
    if not isinstance(log,dict) or 'decisions' not in log: raise ValueError("`decision_log` must be created by `create_gazepoint_analysis_decision_log()`.")


def _value(v):
    if pd.isna(v): return "NA"
    if isinstance(v,float) and v.is_integer(): return str(int(v))
    return str(v)


def _prop(v):
    if pd.isna(v): return "NA"
    return f"{float(v):.3f}"


def _validation_sentence(validation):
    _validate_named_validation(validation)
    return "Package validation: " + "; ".join(f"{k} = {v}" for k,v in validation.items()) + "."


def _decision_summary(log):
    _validate_decision_log(log)
    dec=log['decisions']
    if not isinstance(dec,pd.DataFrame): raise ValueError("decision_log decisions must be a data frame")
    overview=pd.DataFrame([{'n_decisions':len(dec)}])
    by_stage=(dec.groupby('stage',dropna=False).size().reset_index(name='n_decisions') if 'stage' in dec else pd.DataFrame(columns=['stage','n_decisions']))
    return {'overview':overview,'by_stage':by_stage}


def _table_lines(df):
    if df is None or not isinstance(df,pd.DataFrame) or df.empty: return ["<no rows>"]
    return df.to_string(index=False).splitlines()


def _warning_lines(warnings):
    if warnings is None: return []
    if isinstance(warnings,pd.DataFrame):
        if warnings.empty: return []
        return warnings.to_string(index=False).splitlines()
    if isinstance(warnings,(list,tuple)): return [str(x) for x in warnings]
    return [str(warnings)]


def _collect_warnings(**objects):
    out=[]
    for name,obj in objects.items():
        if obj is None: continue
        w=obj.get('warnings',[])
        if isinstance(w,pd.DataFrame):
            if not w.empty:
                for _,r in w.iterrows(): out.append(f"{name}: " + "; ".join(map(str,r.tolist())))
        elif isinstance(w,(list,tuple)): out.extend(f"{name}: {x}" for x in w)
        elif w: out.append(f"{name}: {w}")
    return out


def create_gazepoint_methods_section(export_profile=None,design_audit=None,event_audit=None,condition_audit=None,decision_log=None,package_version='2.0.0',validation=None,include_guardrails=True):
    for obj,name in [(export_profile,'export_profile'),(design_audit,'design_audit'),(event_audit,'event_audit'),(condition_audit,'condition_audit')]: _validate_audit(obj,name)
    _validate_decision_log(decision_log); package_version=_scalar(str(package_version),'package_version'); include_guardrails=_logical(include_guardrails,'include_guardrails'); _validate_named_validation(validation)
    txt=[f"Methods were implemented with gpbiometrics {package_version} semantics in the gpbiometricspy Python port."]
    if export_profile is not None:
        ov=export_profile['overview'].iloc[0]; txt.append(f"The Gazepoint export folder was profiled before analysis; {_value(ov.get('n_files', 'NA'))} file(s) were identified and {_value(ov.get('n_readable_files', 'NA'))} were readable.")
    if design_audit is not None:
        ov=design_audit['overview'].iloc[0]; txt.append(f"An experiment-design audit identified {_value(ov.get('n_participants','NA'))} participant(s), {_value(ov.get('n_trials','NA'))} trial identifier(s), and {_value(ov.get('n_conditions','NA'))} condition(s).")
    if event_audit is not None:
        ov=event_audit['overview'].iloc[0]; txt.append(f"Event coverage was audited across {_value(ov.get('n_units','NA'))} analysis unit(s) and {_value(ov.get('n_expected_events','NA'))} expected event label(s). {_value(ov.get('n_complete_units','NA'))} unit(s) contained all expected events (coverage proportion = {_prop(ov.get('complete_unit_prop',float('nan')))}).")
    if condition_audit is not None:
        ov=condition_audit['overview'].iloc[0]; complete=bool(ov.get('complete_participant_condition_grid',False)); txt.append(f"Condition balance was audited before model-ready data preparation. The condition-balance audit identified {_value(ov.get('n_participants','NA'))} participant(s), {_value(ov.get('n_conditions','NA'))} condition(s), and {_value(ov.get('n_trials','NA'))} participant-condition trial unit(s); the participant-condition grid was {'complete' if complete else 'incomplete'}.")
    if decision_log is not None:
        s=_decision_summary(decision_log); txt.append(f"Workflow decisions were recorded in a structured analysis decision log. The log contained {_value(s['overview'].iloc[0]['n_decisions'])} decision record(s), covering exclusions, preprocessing choices, quality-control decisions, analysis settings, or reviewer-facing notes where applicable.")
    if validation is not None: txt.append(_validation_sentence(validation))
    if include_guardrails: txt.append("All biometric, gaze-linked, and time-course outputs were treated as workflow descriptors. They were not interpreted as direct measures of emotion, stress, cognition, preference, health status, diagnosis, mechanism, or precise temporal onset.")
    return ReportText(txt,'methods_section')


def create_gazepoint_qc_supplement(export_profile=None,design_audit=None,event_audit=None,condition_audit=None,decision_log=None,title='Gazepoint workflow quality-control supplement'):
    for obj,name in [(export_profile,'export_profile'),(design_audit,'design_audit'),(event_audit,'event_audit'),(condition_audit,'condition_audit')]: _validate_audit(obj,name)
    _validate_decision_log(decision_log); title=_scalar(title,'title'); txt=[title,'='*len(title)]
    for obj,heading in [(export_profile,'Export-folder profile'),(design_audit,'Experiment-design audit'),(event_audit,'Event-coverage audit'),(condition_audit,'Condition-balance audit')]:
        if obj is not None: txt += ['',heading,'-'*len(heading),*_table_lines(obj['overview']),*_warning_lines(obj.get('warnings'))]
    if decision_log is not None:
        s=_decision_summary(decision_log); txt += ['','Analysis decision log','---------------------',*_table_lines(s['overview']),'','Decision counts by stage:',*_table_lines(s['by_stage'])]
    if len(txt)<=2: txt += ['','No audit objects were supplied. The supplement template was created without workflow-specific summaries.']
    return ReportText(txt,'qc_supplement')


def create_gazepoint_reproducibility_statement(decision_log=None,package_version='2.0.0',repository_url=None,validation=None,data_statement=None,include_guardrails=True):
    _validate_decision_log(decision_log); package_version=_scalar(str(package_version),'package_version'); include_guardrails=_logical(include_guardrails,'include_guardrails'); _validate_named_validation(validation)
    txt=[f"Analyses were supported by gpbiometrics {package_version}. The workflow was structured to preserve auditability of import, quality-control, preprocessing, analysis-readiness, and reporting decisions."]
    if repository_url is not None and not (isinstance(repository_url,float) and math.isnan(repository_url)):
        txt.append(f"Repository, package source, and documentation are available at: {repository_url}.")
    if decision_log is not None:
        s=_decision_summary(decision_log); txt.append(f"A structured analysis decision log recorded {_value(s['overview'].iloc[0]['n_decisions'])} workflow decision(s).")
    if validation is not None: txt.append(_validation_sentence(validation))
    if data_statement is not None and not (isinstance(data_statement,float) and math.isnan(data_statement)): txt.append(str(data_statement))
    if include_guardrails: txt.append("The workflow is conservative: biometric and gaze-linked outputs are documented as signal-processing and reporting products, not as automatic labels of emotion, stress, cognition, preference, health status, diagnosis, mechanism, or exact temporal onset.")
    return ReportText(txt,'reproducibility_statement')


def create_gazepoint_audit_report_section(export_profile=None,design_audit=None,event_audit=None,condition_audit=None,decision_log=None,include_warnings=True):
    for obj,name in [(export_profile,'export_profile'),(design_audit,'design_audit'),(event_audit,'event_audit'),(condition_audit,'condition_audit')]: _validate_audit(obj,name)
    _validate_decision_log(decision_log); include_warnings=_logical(include_warnings,'include_warnings'); txt=['Gazepoint workflow audit summary']
    if export_profile is not None:
        ov=export_profile['overview'].iloc[0]; txt.append(f"The export-folder profile included {_value(ov.get('n_files','NA'))} matching file(s), {_value(ov.get('n_readable_files','NA'))} readable file(s), and {_value(ov.get('n_read_errors','NA'))} read error(s).")
    if design_audit is not None:
        ov=design_audit['overview'].iloc[0]; txt.append(f"The design audit identified {_value(ov.get('n_participants','NA'))} participant(s), {_value(ov.get('n_trials','NA'))} trial identifier(s), and {_value(ov.get('n_conditions','NA'))} condition(s).")
    if event_audit is not None:
        ov=event_audit['overview'].iloc[0]; txt.append(f"The event-coverage audit evaluated {_value(ov.get('n_units','NA'))} unit(s), with complete expected-event coverage in {_value(ov.get('n_complete_units','NA'))} unit(s).")
    if condition_audit is not None:
        ov=condition_audit['overview'].iloc[0]; complete=bool(ov.get('complete_participant_condition_grid',False)); txt.append(f"The condition-balance audit indicated a trial-imbalance ratio of {_prop(ov.get('trial_imbalance_ratio',float('nan')))} and a {'complete' if complete else 'incomplete'} participant-condition grid.")
    if decision_log is not None:
        s=_decision_summary(decision_log); txt.append(f"The decision log contained {_value(s['overview'].iloc[0]['n_decisions'])} recorded workflow decision(s).")
    if len(txt)==1: txt.append('No audit objects were supplied. The report section was created without workflow-specific summaries.')
    if include_warnings:
        warnings=_collect_warnings(export_profile=export_profile,design_audit=design_audit,event_audit=event_audit,condition_audit=condition_audit)
        txt.append(f"Audit warnings: {len(warnings)} warning records were identified." if warnings else 'No audit warnings were recorded in the supplied objects.')
    return ReportText(txt,'audit_report_section')
