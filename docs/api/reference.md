# Frozen 406-function API reference

Every function below is a member of the frozen `gpbiometrics 2.0.0` export contract and is registered as implemented in `gpbiometricspy`.

The signature shown is the live Python signature. For exact R source/signature provenance see `reference/r-export-inventory.csv`.

## `add_gazepoint_decision`

```python
add_gazepoint_decision(log, stage, object_type, decision, object_id=None, reason=None, function_name=None, parameter=None, value=None, reviewer_note=None, timestamp=None)
```

## `align_gazepoint_biometrics_to_ttl`

```python
align_gazepoint_biometrics_to_ttl(data, ttl_cols=None, event_col=None, ttl_valid_col=None, time_col=None, sample_col=None, group_cols=None, participant_col=None, stimulus_col=None, trial_col=None, event_value=None, valid_values=(True, 1, '1'), event_edge='rising', pre_window_ms=1000, post_window_ms=5000, pre_window_samples=None, post_window_samples=None, collapse_nearby_ms=0, require_valid_ttl=True)
```

## `align_gazepoint_streams_by_events`

```python
align_gazepoint_streams_by_events(reference, target, reference_events, target_events, reference_time_col=None, target_time_col=None, reference_event_time_col=None, target_event_time_col=None, event_id_col=None, method='linear', include_streams=True)
```

## `align_gazepoint_to_eeg`

```python
align_gazepoint_to_eeg(gazepoint, gazepoint_events, eeg_events, gazepoint_time_col=None, gazepoint_event_time_col=None, eeg_event_time_col=None, eeg_event_sample_col=None, gazepoint_event_id_col=None, eeg_event_id_col=None, gazepoint_time_unit='auto', eeg_time_unit='auto', eeg_sampling_rate_hz=None, method='offset', match_by='auto', robust=True, maximum_residual_s=None, residual_action='error', output_col='time_eeg_s')
```

## `analyze_gazepoint_ac_susceptance`

```python
analyze_gazepoint_ac_susceptance(dat, conductance_col=None, susceptance_col=None, admittance_col=None, phase_col=None, frequency_col=None, time_col=None, group_cols=None)
```

## `analyze_gazepoint_cardiorespiratory_causality`

```python
analyze_gazepoint_cardiorespiratory_causality(dat, respiration_col, cardiac_col, time_col=None, group_cols=None, lag_order=3, min_rows=30, standardise=True)
```

## `analyze_gazepoint_skin_potential`

```python
analyze_gazepoint_skin_potential(dat, sp_col, time_col, group_cols=None, response_direction='both', response_threshold=None, min_response_distance_s=1)
```

## `anonymize_gazepoint_data`

```python
anonymize_gazepoint_data(data, id_cols, prefix='P', width=3, keep_mapping=True)
```

## `assert_gazepoint_columns`

```python
assert_gazepoint_columns(data, required, optional=(), mode='error', ignore_case=True)
```

## `assess_gazepoint_hrp_waveform_quality`

```python
assess_gazepoint_hrp_waveform_quality(data, hrp_col=None, time_col=None, group_cols=None, sampling_rate=None, time_unit='auto', min_rows=20, min_finite_prop=0.8, max_flat_prop=0.95, flat_tolerance=1e-08, max_gap_multiplier=3)
```

## `assess_gazepoint_sampling_irregularity`

```python
assess_gazepoint_sampling_irregularity(data, time_col=None, group_cols=None, nominal_rate_hz=None, large_gap_factor=3)
```

## `assign_gazepoint_aoi`

```python
assign_gazepoint_aoi(data, aois, x_col=None, y_col=None, aoi_label_col='aoi', format='auto', aoi_id_col=None, data_match_cols=None, aoi_match_cols=None, xmin_col='xmin', xmax_col='xmax', ymin_col='ymin', ymax_col='ymax', vertex_x_col='vertex_x', vertex_y_col='vertex_y', priority_col=None, overlap='priority', boundary='inside', output_col='AOI', match_count_col='aoi_match_count', ambiguous_col='aoi_ambiguous', status_col='aoi_assignment_status', all_separator='|', overwrite=False)
```

## `audit_gazepoint_beats`

```python
audit_gazepoint_beats(data, ibi_col=None, beat_time_col=None, group_cols=None, min_ibi=300, max_ibi=2000, duplicate_tolerance=0, max_relative_change=None)
```

## `audit_gazepoint_biometric_missingness`

```python
audit_gazepoint_biometric_missingness(data, columns=None)
```

## `audit_gazepoint_biometric_sampling`

```python
audit_gazepoint_biometric_sampling(data, group_columns=None, time_column=None, time_unit='seconds', expected_rate_hz=60, tolerance_hz=5)
```

## `audit_gazepoint_biometric_sync_drift`

```python
audit_gazepoint_biometric_sync_drift(data, time_col=None, group_cols=None, signal_pairs=None, signal_cols=None, reference_signal_col=None, max_lag=1000, lag_step=None, drift_tolerance=None, method='pearson', min_complete_pairs=20, use_first_difference=False, include_reset_segments=True)
```

## `audit_gazepoint_biometrics_file`

```python
audit_gazepoint_biometrics_file(path=None, data=None, expected_modalities=('time', 'eda', 'ppg', 'hr', 'ibi', 'pupil', 'gaze', 'events'), time_col=None, standardize=True, include_data=False, long_gap_s=None)
```

## `audit_gazepoint_condition_balance`

```python
audit_gazepoint_condition_balance(data, participant_col, condition_col, trial_col=None, expected_conditions=None)
```

## `audit_gazepoint_dataset_structure`

```python
audit_gazepoint_dataset_structure(root, expected_dirs=None, expected_files=None, expected_patterns=None, allowed_extensions=None, require_sidecars=False)
```

## `audit_gazepoint_distributional_drift`

```python
audit_gazepoint_distributional_drift(dat, signal_cols, session_col='session', participant_col=None, reference_session=None, bins=10, psi_warn=0.1, psi_fail=0.25)
```

## `audit_gazepoint_eda_artifacts`

```python
audit_gazepoint_eda_artifacts(data, signal_col=None, time_col=None, group_cols=None, prefer_gsr_us=True, jump_threshold_sd=6, slope_threshold_sd=6, flat_run_length=20, zero_run_length=20, saturation_min=None, saturation_max=None, negative_allowed=None)
```

## `audit_gazepoint_engagement_dial`

```python
audit_gazepoint_engagement_dial(data, value_column='DIAL', validity_column='DIALV', min_value=0, max_value=1, jump_threshold=None)
```

## `audit_gazepoint_event_coverage`

```python
audit_gazepoint_event_coverage(data, event_col, participant_col=None, trial_col=None, unit_cols=None, expected_events=None)
```

## `audit_gazepoint_experiment_design`

```python
audit_gazepoint_experiment_design(data, participant_col='participant', trial_col=None, condition_col=None, session_col=None, expected_conditions=None, min_trials_per_condition=1)
```

## `audit_gazepoint_export_schema`

```python
audit_gazepoint_export_schema(data, expected_roles=None, dictionary=None, strict=False)
```

## `audit_gazepoint_gsr_quality`

```python
audit_gazepoint_gsr_quality(data, value_column=None, validity_column='GSRV', min_value=0, max_value=100, jump_threshold=None)
```

## `audit_gazepoint_gsr_units`

```python
audit_gazepoint_gsr_units(dat, gsr_col='GSR', convert=False, output_col=None, resistance_to_us_factor=1000000)
```

## `audit_gazepoint_hr_quality`

```python
audit_gazepoint_hr_quality(data, value_column='HR', validity_column='HRV', min_value=30, max_value=220, jump_threshold=25)
```

## `audit_gazepoint_ibi_quality`

```python
audit_gazepoint_ibi_quality(data, ibi_col=None, group_cols=None, time_col=None, unit='auto', min_ibi_ms=300, max_ibi_ms=2000, max_jump_ms=500)
```

## `audit_gazepoint_interoperability_versions`

```python
audit_gazepoint_interoperability_versions(manifest=None, include_python=True, strict=False)
```

## `audit_gazepoint_pipeline_steps`

```python
audit_gazepoint_pipeline_steps(pipeline, expected_steps=None, required_order=None, allow_extra=True)
```

## `audit_gazepoint_preregistration_consistency`

```python
audit_gazepoint_preregistration_consistency(checklist=None, evidence=None, require_required_fields=True)
```

## `audit_gazepoint_pupil_luminance`

```python
audit_gazepoint_pupil_luminance(data, pupil_col=None, luminance_col=None, group_cols=None, threshold=0.3, method='pearson')
```

## `audit_gazepoint_release_readiness`

```python
audit_gazepoint_release_readiness(path='.', required_files=('DESCRIPTION', 'NAMESPACE', 'R', 'man', 'tests/testthat', '_pkgdown.yml'), expected_exports=None, roadmap_terms=None, require_pkgdown=True)
```

## `audit_gazepoint_session_comparability`

```python
audit_gazepoint_session_comparability(data, metric_cols, group_cols=None, method='both', z_threshold=2, iqr_multiplier=1.5)
```

## `audit_gazepoint_signal_activity`

```python
audit_gazepoint_signal_activity(data, signal_cols=None, group_cols=None, zero_is_inactive=True, min_unique_nonzero=2, missing_as_inactive=True)
```

## `audit_gazepoint_smoke_privacy`

```python
audit_gazepoint_smoke_privacy(x, private_values=None)
```

## `audit_gazepoint_stabilization_period`

```python
audit_gazepoint_stabilization_period(dat, time_col='CNT', group_cols=None, stabilization_minutes=10, action='flag', output_col='in_stabilization_period', time_units='auto')
```

## `audit_gazepoint_time_resets`

```python
audit_gazepoint_time_resets(data, time_col=None, group_cols=None, allow_ties=True, split_on_negative_step=True, return_reindexed_time=False, min_segment_rows=1)
```

## `audit_gazepoint_timecourse_grid`

```python
audit_gazepoint_timecourse_grid(data, subject, condition, time, value=None, max_report_cells=1000)
```

## `baseline_correct_gazepoint_gsr`

```python
baseline_correct_gazepoint_gsr(data, baseline_rows, value_column=None, validity_column='GSRV', group_columns=None, output_column=None, summary='mean', exclude_zero=True)
```

## `baseline_correct_gazepoint_hr`

```python
baseline_correct_gazepoint_hr(data, baseline_rows, value_column='HR', validity_column='HRV', group_columns=None, output_column=None, summary='mean', exclude_zero=True)
```

## `baseline_correct_gazepoint_pupil`

```python
baseline_correct_gazepoint_pupil(dat, pupil_col=None, time_col='time', stimulus_onset_col=None, trial_cols=None, baseline_window=(-250, -50), baseline_function='median', correction='subtract', suffix='_baseline_corrected', min_baseline_rows=2, overwrite=False)
```

## `build_gazepoint_aoi_timecourse`

```python
build_gazepoint_aoi_timecourse(data, time_col=None, aoi_col=None, x_col=None, y_col=None, aoi_definitions=None, group_cols=None, bin_width_s=0.1, valid_col=None, include_empty=True)
```

## `calculate_gazepoint_rsa`

```python
calculate_gazepoint_rsa(dat: 'pd.DataFrame', ibi_col: 'str' = 'IBI', time_col: 'str' = 'CNT', group_cols: 'Iterable[str] | None' = None, pdr=None, resp_rate_hz: 'float | None' = None, respiration_band=(0.12, 0.4), resample_rate: 'float' = 4)
```

## `check_gazepoint_bids`

```python
check_gazepoint_bids(root, subject_pattern='^sub-[A-Za-z0-9]+$', recursive=True, expected_files=('dataset_description.json', 'participants.tsv'), gazepoint_patterns=('all[_-]?gaze', 'fixation', 'summary', 'biometric', 'eda', 'gsr', 'ecg', 'ppg', 'hr', 'ibi'))
```

## `check_gazepoint_biometric_columns`

```python
check_gazepoint_biometric_columns(data)
```

## `check_gazepoint_plot_contract`

```python
check_gazepoint_plot_contract(plot, require_plot_data=True, require_settings=True)
```

## `check_gazepoint_ppg_binary_quality`

```python
check_gazepoint_ppg_binary_quality(measures=None, peaks=None, min_peaks=5, bpm_range=(40, 180), max_missing_prop=0.25)
```

## `check_gazepoint_pyhrv_interval`

```python
check_gazepoint_pyhrv_interval(nni_ms, min_ms=250, max_ms=2500)
```

## `chunk_gazepoint_biometrics`

```python
chunk_gazepoint_biometrics(dat, time_col='CNT', group_cols=None, chunk_seconds=60, start_time=None, chunk_col='chunk_id', episode_col='episode_id', include_partial=False)
```

## `classify_gazepoint_eda_response_pattern`

```python
classify_gazepoint_eda_response_pattern(data, response_col=None, group_cols=None, summary_function='max_abs', no_response_threshold=0.01, low_response_threshold=0.05, moderate_response_threshold=0.2)
```

## `classify_gazepoint_scr_intervals`

```python
classify_gazepoint_scr_intervals(dat, response_time_col=None, stimulus_onset_col=None, latency_col=None, output_col='scr_interval', latency_output_col='scr_latency_s', fir=(1, 4), sir=(4, 7), tir=(7, 10))
```

## `classify_gazepoint_signal_quality`

```python
classify_gazepoint_signal_quality(quality, rules=None)
```

## `clean_gazepoint_pupil`

```python
clean_gazepoint_pupil(data, pupil_cols=None, time_col=None, blink_col=None, max_gap_s=None, method='linear', suffix='_clean', prefer_existing=False, **kwargs)
```

## `clean_gazepoint_pupil_signal`

```python
clean_gazepoint_pupil_signal(data, pupil_cols=None, time_col=None, group_cols=None, validity_cols=None, method='linear', max_gap=inf, spike_mad=6, combine='all', min_blink_samples=1, suffix='_clean', keep_flags=True)
```

## `clean_gazepoint_rr_intervals`

```python
clean_gazepoint_rr_intervals(rr_ms, method='quotient', group_col='group', quotient_threshold=0.2, iqr_multiplier=1.5, z_threshold=3.5)
```

## `combine_gazepoint_marker_channels_pspm_style`

```python
combine_gazepoint_marker_channels_pspm_style(data, marker_cols=None, time_col=None, sampling_rate_hz=None, group_cols=None, combined_col='pspm_marker')
```

## `compare_gazepoint_conditions_bootstrap`

```python
compare_gazepoint_conditions_bootstrap(data, outcome_col, condition_col, participant_col=None, condition_levels=None, paired=False, by_cols=None, statistic='mean_difference', n_boot=2000, conf_level=0.95, seed=None, na_rm=True)
```

## `compare_gazepoint_export_profiles`

```python
compare_gazepoint_export_profiles(*profiles, labels=None)
```

## `compare_gazepoint_hr_ibi_consistency`

```python
compare_gazepoint_hr_ibi_consistency(data, hr_col='HR', ibi_col='IBI', time_col=None, group_cols=None, unit='auto', max_abs_diff_bpm=10, max_rel_diff_prop=0.15)
```

## `compare_gazepoint_pyhrv_psd_methods`

```python
compare_gazepoint_pyhrv_psd_methods(nni_ms, time_s=None, methods=('welch', 'lomb', 'ar'), plot=False)
```

## `compute_gazepoint_engagement_index`

```python
compute_gazepoint_engagement_index(dial, time=None, threshold=50, group=None, return_='data', **kwargs)
```

## `compute_gazepoint_hrv_wavelet_psd`

```python
compute_gazepoint_hrv_wavelet_psd(rr_intervals, time=None, bands=None, max_scale=None)
```

## `compute_gazepoint_ppg_frequency_measures`

```python
compute_gazepoint_ppg_frequency_measures(peaks=None, rr_ms=None, rr_time_s=None, group_col='group', method='welch', resample_hz=4, bands=None, welch_window_seconds=64, welch_overlap=0.5)
```

## `compute_gazepoint_ppg_measures`

```python
compute_gazepoint_ppg_measures(peaks, group_col='group')
```

## `compute_gazepoint_ppg_template_similarity`

```python
compute_gazepoint_ppg_template_similarity(data, time_col=None, ppg_col=None, peaks=None, window_s=(-0.25, 0.45), sampling_rate_hz=None, n_grid=101, similarity_threshold=0.8)
```

## `compute_gazepoint_pyhrv_ar_psd`

```python
compute_gazepoint_pyhrv_ar_psd(nni_ms, time_s=None, resample_hz=4, order=None)
```

## `compute_gazepoint_pyhrv_dfa`

```python
compute_gazepoint_pyhrv_dfa(nni_ms, scales=None)
```

## `compute_gazepoint_pyhrv_frequency_domain`

```python
compute_gazepoint_pyhrv_frequency_domain(nni_ms, time_s=None, method='welch')
```

## `compute_gazepoint_pyhrv_heart_rate`

```python
compute_gazepoint_pyhrv_heart_rate(nni_ms)
```

## `compute_gazepoint_pyhrv_hr_parameters`

```python
compute_gazepoint_pyhrv_hr_parameters(nni_ms)
```

## `compute_gazepoint_pyhrv_lomb_psd`

```python
compute_gazepoint_pyhrv_lomb_psd(nni_ms, time_s=None, min_hz=0.003, max_hz=0.4, n_freq=512)
```

## `compute_gazepoint_pyhrv_nn20`

```python
compute_gazepoint_pyhrv_nn20(nni_ms)
```

## `compute_gazepoint_pyhrv_nn50`

```python
compute_gazepoint_pyhrv_nn50(nni_ms)
```

## `compute_gazepoint_pyhrv_nn_diff`

```python
compute_gazepoint_pyhrv_nn_diff(nni_ms, absolute=False)
```

## `compute_gazepoint_pyhrv_nni_differences_parameters`

```python
compute_gazepoint_pyhrv_nni_differences_parameters(nni_ms)
```

## `compute_gazepoint_pyhrv_nni_parameters`

```python
compute_gazepoint_pyhrv_nni_parameters(nni_ms)
```

## `compute_gazepoint_pyhrv_nnxx`

```python
compute_gazepoint_pyhrv_nnxx(nni_ms, threshold_ms=50)
```

## `compute_gazepoint_pyhrv_nonlinear`

```python
compute_gazepoint_pyhrv_nonlinear(nni_ms)
```

## `compute_gazepoint_pyhrv_poincare`

```python
compute_gazepoint_pyhrv_poincare(nni_ms, plot=False)
```

## `compute_gazepoint_pyhrv_psd_waterfall`

```python
compute_gazepoint_pyhrv_psd_waterfall(nni_ms, segment_seconds=300, method='welch', plot=False)
```

## `compute_gazepoint_pyhrv_rmssd`

```python
compute_gazepoint_pyhrv_rmssd(nni_ms)
```

## `compute_gazepoint_pyhrv_sample_entropy`

```python
compute_gazepoint_pyhrv_sample_entropy(nni_ms, m=2, r=None)
```

## `compute_gazepoint_pyhrv_sdann`

```python
compute_gazepoint_pyhrv_sdann(nni_ms, segment_seconds=300)
```

## `compute_gazepoint_pyhrv_sdnn`

```python
compute_gazepoint_pyhrv_sdnn(nni_ms)
```

## `compute_gazepoint_pyhrv_sdnn_index`

```python
compute_gazepoint_pyhrv_sdnn_index(nni_ms, segment_seconds=300)
```

## `compute_gazepoint_pyhrv_sdsd`

```python
compute_gazepoint_pyhrv_sdsd(nni_ms)
```

## `compute_gazepoint_pyhrv_time_domain`

```python
compute_gazepoint_pyhrv_time_domain(nni_ms, segment_seconds=300)
```

## `compute_gazepoint_pyhrv_tinn`

```python
compute_gazepoint_pyhrv_tinn(nni_ms, bin_width_ms=7.8125)
```

## `compute_gazepoint_pyhrv_triangular_index`

```python
compute_gazepoint_pyhrv_triangular_index(nni_ms, bin_width_ms=7.8125)
```

## `compute_gazepoint_pyhrv_welch_psd`

```python
compute_gazepoint_pyhrv_welch_psd(nni_ms, time_s=None, resample_hz=4, window_seconds=256, overlap=0.5)
```

## `compute_gazepoint_quality_index`

```python
compute_gazepoint_quality_index(data, metric_cols, directions=None, weights=None, index_col='quality_index', component_prefix='quality_component_', overwrite=False)
```

## `compute_gazepoint_scr_habituation`

```python
compute_gazepoint_scr_habituation(data, amplitude_col=None, trial_col=None, subject_col=None, method='linear', min_trials=3)
```

## `compute_gazepoint_scr_latency`

```python
compute_gazepoint_scr_latency(data, events, time_col=None, eda_col=None, event_time_col=None, event_id_col=None, group_cols=None, baseline_window_s=(-1, 0), response_window_s=(0, 5), onset_threshold=0.01, recovery_fraction=0.5)
```

## `compute_gazepoint_signal_band_power`

```python
compute_gazepoint_signal_band_power(x, sampling_rate_hz=None, bands=None, relative=True)
```

## `compute_gazepoint_signal_correlation`

```python
compute_gazepoint_signal_correlation(x, y, method='pearson', lag_max=None)
```

## `compute_gazepoint_signal_lag_matrix`

```python
compute_gazepoint_signal_lag_matrix(data, signal_cols=None, time_col=None, group_cols=None, max_lag_s=2, lag_step_s=None, min_overlap=10)
```

## `compute_gazepoint_signal_phase_locking`

```python
compute_gazepoint_signal_phase_locking(x, y, sampling_rate_hz, band=None)
```

## `compute_gazepoint_signal_power_spectrum`

```python
compute_gazepoint_signal_power_spectrum(x, sampling_rate_hz, detrend=True)
```

## `compute_gazepoint_signal_quality`

```python
compute_gazepoint_signal_quality(data, signal_cols, group_cols=None, flatline_tolerance=0, long_missing_run_threshold=10, long_constant_run_threshold=10, spike_z=4, extreme_z=4)
```

## `convert_gazepoint_gsr_to_conductance`

```python
convert_gazepoint_gsr_to_conductance(data, gsr_col=None, output_col='GSR_US', input_unit='auto', overwrite=False)
```

## `correct_gazepoint_beats`

```python
correct_gazepoint_beats(audit, action='mask', corrected_col='ibi_corrected', local_window=5, overwrite=False, **kwargs)
```

## `correct_gazepoint_eda_temperature`

```python
correct_gazepoint_eda_temperature(dat, eda_col='GSR_US', temperature_cols=None, group_cols=None, time_col=None, output_col='eda_temperature_adjusted', fitted_col='eda_temperature_fitted', model_by_group=True, add_intercept_mean=True)
```

## `correct_gazepoint_ppg_hampel`

```python
correct_gazepoint_ppg_hampel(x, sampling_rate_hz, window_seconds=1, n_sigmas=3)
```

## `correct_gazepoint_rri_artifacts_local`

```python
correct_gazepoint_rri_artifacts_local(rri_ms, method='local_median', window_intervals=5, threshold=0.2, replacement='local_median')
```

## `create_gazepoint_analysis_decision_log`

```python
create_gazepoint_analysis_decision_log(study_id=None, analyst=None, description=None)
```

## `create_gazepoint_analysis_manifest`

```python
create_gazepoint_analysis_manifest(files=None, settings=None, outputs=None, exclusions=None, path=None, include_session=True)
```

## `create_gazepoint_audit_index`

```python
create_gazepoint_audit_index(audits=None, audit_ids=None, include_summary_rows=False)
```

## `create_gazepoint_audit_report_section`

```python
create_gazepoint_audit_report_section(export_profile=None, design_audit=None, event_audit=None, condition_audit=None, decision_log=None, include_warnings=True)
```

## `create_gazepoint_biometrics_checklist`

```python
create_gazepoint_biometrics_checklist(data, require_active_signal=True)
```

## `create_gazepoint_biometrics_feature_inventory`

```python
create_gazepoint_biometrics_feature_inventory(include_internal=False)
```

## `create_gazepoint_biometrics_methods_text`

```python
create_gazepoint_biometrics_methods_text(checklist=None, data=None, include_cautions=True)
```

## `create_gazepoint_biometrics_report`

```python
create_gazepoint_biometrics_report(data=None, workflow=None, validation=None, quality=None, sampling=None, missingness=None, exclusions=None, report_tables=None, methods_text=None, checklist=None, title='Gazepoint Biometrics report', subtitle=None, output_file=None, format='markdown', include_timestamp=False, overwrite=False, max_table_rows=20)
```

## `create_gazepoint_biometrics_report_tables`

```python
create_gazepoint_biometrics_report_tables(workflow=None, validation=None, quality=None, sampling=None, diagnostics=None, exclusion_recommendations=None, ttl_events=None, max_ttl_events=20)
```

## `create_gazepoint_dictionary`

```python
create_gazepoint_dictionary(data=None, file_paths=None, units=None, descriptions=None, required_cols=None, write_path=None)
```

## `create_gazepoint_eda_analysis_pipeline`

```python
create_gazepoint_eda_analysis_pipeline(include_external_bridges=True, include_model_templates=True, include_reporting_guidance=True, style='compact')
```

## `create_gazepoint_eye_methods_text`

```python
create_gazepoint_eye_methods_text(sampling_rate_hz, device_model='Gazepoint GP3', calibration_points=9, binocular=True, software='Gazepoint Analysis', screen_resolution=None, viewing_distance_cm=None, coordinate_space=None, preprocessing=None, fixation_detection=None, aoi_definition=None, synchronization=None, exclusions=None, tense='past', include_package_version=True)
```

## `create_gazepoint_heartpy_report`

```python
create_gazepoint_heartpy_report(detection, output_dir=None, prefix='gazepoint_heartpy')
```

## `create_gazepoint_methods_section`

```python
create_gazepoint_methods_section(export_profile=None, design_audit=None, event_audit=None, condition_audit=None, decision_log=None, package_version='2.0.0', validation=None, include_guardrails=True)
```

## `create_gazepoint_pipeline_map`

```python
create_gazepoint_pipeline_map(steps=None, edges=None, pipeline_id='gazepoint_pipeline', include_default=True)
```

## `create_gazepoint_preregistration_checklist`

```python
create_gazepoint_preregistration_checklist(study_id=None, include_optional=True, custom_items=None)
```

## `create_gazepoint_preregistration_template`

```python
create_gazepoint_preregistration_template(study_title='Gazepoint biometrics study', signal_standardization='within_participant_z', artifact_rules='kleckner_style', eda_min_us=0.01, eda_max_us=100, rapid_change_threshold=20, output_file=None)
```

## `create_gazepoint_pspm_glm_design`

```python
create_gazepoint_pspm_glm_design(events, time, time_col=None, onset_col='onset_time_s', condition_col='condition', duration_col=None, response='scr', response_length_s=20, include_derivative=False, add_intercept=True)
```

## `create_gazepoint_pyhrv_time_vector`

```python
create_gazepoint_pyhrv_time_vector(nni_ms, start_s=0)
```

## `create_gazepoint_qc_supplement`

```python
create_gazepoint_qc_supplement(export_profile=None, design_audit=None, event_audit=None, condition_audit=None, decision_log=None, title='Gazepoint workflow quality-control supplement')
```

## `create_gazepoint_quality_dashboard`

```python
create_gazepoint_quality_dashboard(data=None, audit=None, missingness=None, alignment=None, eventlocked=None, title='Gazepoint quality dashboard', output_dir=None)
```

## `create_gazepoint_release_checklist`

```python
create_gazepoint_release_checklist(audit=None, include_optional=True)
```

## `create_gazepoint_reproducibility_statement`

```python
create_gazepoint_reproducibility_statement(decision_log=None, package_version='2.0.0', repository_url=None, validation=None, data_statement=None, include_guardrails=True)
```

## `create_gazepoint_sidecar_template`

```python
create_gazepoint_sidecar_template(dataset_id=None, export_type=None, include_optional=True, custom_fields=None)
```

## `create_gazepoint_trial_regressors`

```python
create_gazepoint_trial_regressors(data, design, pre=0, post=5, time_col=None, event_time_col=None, event_id_col=None, signal_cols=None, subject_col=None, design_subject_col=None, carry_design_cols=None)
```

## `decompose_gazepoint_eda`

```python
decompose_gazepoint_eda(data, signal_col=None, tonic_col=None, phasic_col=None, time_col=None, group_cols=None, window_size=31, output_prefix='eda', overwrite=False)
```

## `denoise_gazepoint_eda_autoencoder`

```python
denoise_gazepoint_eda_autoencoder(dat, eda_col='GSR_US', time_col=None, group_cols=None, model=None, window_samples=128, output_col=None, overwrite=False)
```

## `denoise_gazepoint_eda_wavelet`

```python
denoise_gazepoint_eda_wavelet(dat, eda_col='GSR_US', group_cols=None, output_col=None, levels=3, threshold_multiplier=1, overwrite=False)
```

## `denoise_gazepoint_ppg_autoencoder`

```python
denoise_gazepoint_ppg_autoencoder(dat, ppg_col='HRP', time_col=None, group_cols=None, model=None, window_samples=128, output_col=None, overwrite=False)
```

## `denoise_gazepoint_quantization_noise`

```python
denoise_gazepoint_quantization_noise(dat, signal_cols, resolution, group_cols=None, output_suffix='_quantization_jittered', seed=None, overwrite=False)
```

## `detect_active_biometric_channels`

```python
detect_active_biometric_channels(data)
```

## `detect_gazepoint_biometric_schema`

```python
detect_gazepoint_biometric_schema(data)
```

## `detect_gazepoint_biometric_timebase`

```python
detect_gazepoint_biometric_timebase(data, time_col=None, counter_col=None)
```

## `detect_gazepoint_blinks`

```python
detect_gazepoint_blinks(data, pupil_cols=None, id_cols=None, min_pupil=0, max_pupil=inf, change_threshold=None, extend_samples=0, mask=True, flag_suffix='_blink_flag', clean_suffix='_blink_clean')
```

## `detect_gazepoint_doubly_stochastic_changepoints`

```python
detect_gazepoint_doubly_stochastic_changepoints(dat, signal_col, time_col='CNT', group_cols=None, window_seconds=10, step_seconds=2, threshold_mad_multiplier=6, min_distance_s=5)
```

## `detect_gazepoint_fixations`

```python
detect_gazepoint_fixations(data, time_col=None, x_col=None, y_col=None, group_cols=None, valid_col=None, valid_values=(1, True), time_unit='seconds', sampling_rate_hz=None, coordinate_unit='native', velocity_threshold=None, min_fixation_duration_ms=100, min_saccade_duration_ms=10, max_gap_ms=100, velocity_col='gaze_velocity', class_col='gaze_class', event_id_col='gaze_event_id', overwrite=False)
```

## `detect_gazepoint_nonwear`

```python
detect_gazepoint_nonwear(data, signal_cols, group_cols=None, time_col=None, min_run_length=10, zero_tolerance=0, constant_tolerance=0, low_variance_threshold=None, detect_missing=True, detect_zero=True, detect_constant=True, detect_low_variance=True)
```

## `detect_gazepoint_ppg_onsets`

```python
detect_gazepoint_ppg_onsets(data, signal_col=None, time_col=None, peaks=None, group_cols=None, sampling_rate_hz=None, search_seconds=0.6)
```

## `detect_gazepoint_ppg_peaks`

```python
detect_gazepoint_ppg_peaks(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, bpm_min=40, bpm_max=180, moving_average_seconds=0.75, threshold_offsets=None, reconstruct_clipping=True, enhance_peaks=False, lowpass_hz=None, hampel=False, high_precision=True)
```

## `detect_gazepoint_pupil_blinks`

```python
detect_gazepoint_pupil_blinks(data, pupil_cols=None, time_col=None, group_cols=None, validity_cols=None, invalid_values=(0,), nonpositive_is_missing=True, combine='all', min_blink_samples=1, return_='intervals', **kwargs)
```

## `detect_gazepoint_saccades`

```python
detect_gazepoint_saccades(*args, **kwargs)
```

## `detect_gazepoint_scr_events`

```python
detect_gazepoint_scr_events(data, phasic_col=None, signal_col=None, time_col=None, group_cols=None, threshold=None, min_peak_distance=10, window_size=31)
```

## `detect_gazepoint_scr_peaks`

```python
detect_gazepoint_scr_peaks(data, signal_col=None, phasic_col=None, time_col=None, group_cols=None, prefer_vendor_phasic=True, amplitude_min=0.01, recovery_fraction=0.5, smooth_width=1, min_peak_distance=1)
```

## `detect_gazepoint_time_columns`

```python
detect_gazepoint_time_columns(data)
```

## `detrend_gazepoint_rri_window`

```python
detrend_gazepoint_rri_window(rri_ms, time_s=None, window_seconds=60, method='median')
```

## `detrend_gazepoint_signal`

```python
detrend_gazepoint_signal(data, signal_col=None, time_col=None, group_cols=None, method='linear', span=0.3, preserve_mean=False, suffix='_detrended')
```

## `diagnose_gazepoint_biometrics_workflow`

```python
diagnose_gazepoint_biometrics_workflow(workflow, require_gsr=True, require_hr=True, require_dial=False, max_exclude_window_pct=25, max_review_window_pct=25)
```

## `diagnose_gazepoint_cluster_design`

```python
diagnose_gazepoint_cluster_design(data, subject, condition, time, value=None, design='within', min_subjects=10)
```

## `diagnose_gazepoint_sync_drift`

```python
diagnose_gazepoint_sync_drift(reference, target=None, reference_time_col=None, target_time_col=None, max_pairs=None)
```

## `downsample_gazepoint_data`

```python
downsample_gazepoint_data(data, time_col, signal_cols=None, group_cols=None, interval=None, method='mean', na_rm=True, time_value='start', origin=None)
```

## `enhance_gazepoint_ppg_peaks`

```python
enhance_gazepoint_ppg_peaks(x, sampling_rate_hz, iterations=2)
```

## `epoch_gazepoint_scr`

```python
epoch_gazepoint_scr(data, events, pre, post, time_col=None, signal_col=None, event_time_col=None, event_id_col=None, event_group_cols=None, baseline_window=None, response_window=None, min_amplitude=0.01, min_distance_s=1)
```

## `estimate_gazepoint_breathing_rate_from_ibi`

```python
estimate_gazepoint_breathing_rate_from_ibi(rr_ms, rr_time_s=None, resample_hz=4, breathing_band=(0.1, 0.5))
```

## `estimate_gazepoint_cluster_offset`

```python
estimate_gazepoint_cluster_offset(*args, **kwargs)
```

## `estimate_gazepoint_cluster_onset`

```python
estimate_gazepoint_cluster_onset(*args, **kwargs)
```

## `estimate_gazepoint_eda_recovery_times`

```python
estimate_gazepoint_eda_recovery_times(data, events=None, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, recovery_prop=0.5, max_recovery_seconds=10)
```

## `estimate_gazepoint_lsl_clock_offsets`

```python
estimate_gazepoint_lsl_clock_offsets(stream_name=None, stream_type=None, source_id=None, timeout_s=5, n_estimates=5, pause_s=0.05, python=None, execute=True)
```

## `estimate_gazepoint_respiration_from_ppg`

```python
estimate_gazepoint_respiration_from_ppg(data, ppg_col=None, time_col=None, sampling_rate_hz=None, respiratory_band_hz=(0.1, 0.5), detrend=True)
```

## `estimate_gazepoint_samplerate_datetime`

```python
estimate_gazepoint_samplerate_datetime(datetime, format=None, tz='UTC', robust=True)
```

## `estimate_gazepoint_samplerate_mstimer`

```python
estimate_gazepoint_samplerate_mstimer(mstimer, robust=True)
```

## `estimate_gazepoint_signal_lag`

```python
estimate_gazepoint_signal_lag(data, signal_x_col, signal_y_col, time_col=None, group_cols=None, max_lag=1000, lag_step=None, method='pearson', min_complete_pairs=20, use_first_difference=False)
```

## `export_gazepoint_audit_trail_markdown`

```python
export_gazepoint_audit_trail_markdown(audit_index, summary=None, title='Gazepoint audit trail', include_details=True, max_details=100, file=None)
```

## `export_gazepoint_biometrics_report_bundle`

```python
export_gazepoint_biometrics_report_bundle(bundle=None, output_dir=None, prefix='gpbiometrics_report', tables=None, text=None, plots=None, include_readme=True, include_session_info=True, overwrite=False)
```

## `export_gazepoint_cluster_results`

```python
export_gazepoint_cluster_results(result, path='.', prefix='gazepoint_cluster', overwrite=False)
```

## `export_gazepoint_heartpy_input`

```python
export_gazepoint_heartpy_input(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, output_dir=None, prefix='gazepoint_heartpy')
```

## `export_gazepoint_mne_cluster_input`

```python
export_gazepoint_mne_cluster_input(data, outcome_col, time_col, condition_col, participant_col, condition_a=None, condition_b=None, path=None, prefix='gazepoint_mne_cluster', overwrite=False, aggregate=True)
```

## `export_gazepoint_permuco_cluster_input`

```python
export_gazepoint_permuco_cluster_input(data, outcome_col, time_col, condition_col, participant_col, path=None, prefix='gazepoint_permuco_cluster', overwrite=False, aggregate=True)
```

## `export_gazepoint_permutes_cluster_input`

```python
export_gazepoint_permutes_cluster_input(data, outcome_col, time_col, condition_col, participant_col, path=None, prefix='gazepoint_permutes_cluster', overwrite=False, aggregate=True)
```

## `export_gazepoint_pipeline_dot`

```python
export_gazepoint_pipeline_dot(pipeline, file=None, graph_name='gazepoint_pipeline', rankdir='LR', include_descriptions=False)
```

## `export_gazepoint_pspm_model_estimates`

```python
export_gazepoint_pspm_model_estimates(model, path, format=None, include_predictions=True)
```

## `export_gazepoint_pyhrv_results`

```python
export_gazepoint_pyhrv_results(results, path)
```

## `export_gazepoint_rhrv_input`

```python
export_gazepoint_rhrv_input(data, ibi_col='IBI_clean_ms', group_cols=None, unit='auto', collapse_repeated_intervals=True, repeated_tolerance_ms=1e-08, min_ibi_ms=300, max_ibi_ms=2000, output_dir=None, prefix='gazepoint_rhrv')
```

## `export_gazepoint_to_bids`

```python
export_gazepoint_to_bids(data, bids_root, subject, task, dataset_name=None, recorded_eye='cyclopean', recording='eye1', datatype='beh', session=None, acquisition=None, run=None, timestamp_col=None, x_col=None, y_col=None, include_pupil=True, pupil_col=None, additional_cols=None, timestamp_units='auto', coordinate_units='normalized', pupil_units='arbitrary', sample_coordinate_system='gaze-on-screen', sampling_rate_hz=None, sampling_tolerance=0.05, start_time_s=0, screen_distance_m=None, screen_origin=None, screen_resolution_px=None, screen_size_m=None, screen_refresh_rate_hz=None, stimulus_software_name=None, stimulus_software_version=None, operating_system=None, vision_correction=None, manufacturer='Gazepoint', manufacturers_model_name=None, software_versions=None, device_serial_number=None, eye_tracking_method='P-CR', calibration_type=None, calibration_count=None, average_calibration_error_deg=None, maximal_calibration_error_deg=None, eye_tracker_distance_m=None, raw_data_filters=None, timestamp_origin='Eye-tracker clock', custom_coordinate_system_description=None, column_metadata=None, bids_version='1.11.1', dry_run=False, overwrite=False)
```

## `extract_gazepoint_beats_kmeans`

```python
extract_gazepoint_beats_kmeans(dat, pulse_col='HRP', time_col='CNT', group_cols=None, k=2, peak_polarity='positive', min_distance_s=0.3, sampling_rate=None, seed=None)
```

## `extract_gazepoint_bilateral_eda_asymmetry`

```python
extract_gazepoint_bilateral_eda_asymmetry(dat, left_col, right_col, time_col=None, group_cols=None, output_prefix='beda')
```

## `extract_gazepoint_eda_complexity`

```python
extract_gazepoint_eda_complexity(dat: 'pd.DataFrame', eda_col: 'str' = 'GSR_US', group_cols: 'Iterable[str] | None' = None, min_samples: 'int' = 32, sampen_m: 'int' = 2, sampen_r_multiplier: 'float' = 0.2)
```

## `extract_gazepoint_eda_events_biosppy_style`

```python
extract_gazepoint_eda_events_biosppy_style(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, smoothing_seconds=1, min_amplitude=None, min_distance_seconds=1, onset_window_seconds=4)
```

## `extract_gazepoint_eda_spectral_power`

```python
extract_gazepoint_eda_spectral_power(dat, eda_col='GSR_US', time_col=None, group_cols=None, sampling_rate=None, band=(0.045, 0.25), min_samples=32, detrend=True)
```

## `extract_gazepoint_eda_tvsymp`

```python
extract_gazepoint_eda_tvsymp(dat, eda_col='GSR_US', time_col='CNT', group_cols=None, sampling_rate=None, band=(0.08, 0.24), window_seconds=60, step_seconds=5, min_valid_fraction=0.7, normalise=True)
```

## `extract_gazepoint_edr_pca`

```python
extract_gazepoint_edr_pca(dat, ecg_cols, time_col=None, group_cols=None, n_components=1, scale=True, output_prefix='edr_pca')
```

## `extract_gazepoint_hrv_asymmetry`

```python
extract_gazepoint_hrv_asymmetry(dat: 'pd.DataFrame', ibi_col: 'str' = 'IBI', group_cols: 'Iterable[str] | None' = None, zero_tolerance: 'float' = 0)
```

## `extract_gazepoint_hrv_features`

```python
extract_gazepoint_hrv_features(data, ibi_col='IBI_clean_ms', group_cols=None, unit='auto', min_intervals=3, min_duration_s=30, diff_threshold_ms=50, collapse_repeated_intervals=True, repeated_tolerance_ms=1e-08)
```

## `extract_gazepoint_hrv_fragmentation`

```python
extract_gazepoint_hrv_fragmentation(dat: 'pd.DataFrame', ibi_col: 'str' = 'IBI', group_cols: 'Iterable[str] | None' = None, zero_tolerance: 'float' = 0, short_segment_length: 'int' = 3)
```

## `extract_gazepoint_hrv_fuzzy_csi`

```python
extract_gazepoint_hrv_fuzzy_csi(dat, ibi_col='IBI', group_cols=None, m=2, r_multiplier=0.2, fuzzy_power=2, min_intervals=10)
```

## `extract_gazepoint_hrv_geometric`

```python
extract_gazepoint_hrv_geometric(dat: 'pd.DataFrame', ibi_col: 'str' = 'IBI', group_cols: 'Iterable[str] | None' = None, bin_width: 'float | None' = None)
```

## `extract_gazepoint_hrv_nonlinear`

```python
extract_gazepoint_hrv_nonlinear(dat: 'pd.DataFrame', ibi_col: 'str' = 'IBI', group_cols: 'Iterable[str] | None' = None, min_intervals: 'int' = 10, sampen_m: 'int' = 2, sampen_r_multiplier: 'float' = 0.2, mse_scales: 'Iterable[int]' = range(1, 6))
```

## `extract_gazepoint_hrv_rcmse`

```python
extract_gazepoint_hrv_rcmse(dat, ibi_col='IBI', group_cols=None, scales=range(1, 11), m=2, r_multiplier=0.2, min_intervals=20)
```

## `extract_gazepoint_hrv_rqa`

```python
extract_gazepoint_hrv_rqa(dat: 'pd.DataFrame', ibi_col: 'str' = 'IBI', group_cols: 'Iterable[str] | None' = None, embedding_dimension: 'int' = 2, delay: 'int' = 1, radius: 'float | None' = None, radius_multiplier: 'float' = 0.2, min_line_length: 'int' = 2)
```

## `extract_gazepoint_markerinfo_pspm_style`

```python
extract_gazepoint_markerinfo_pspm_style(data, marker_cols=None, time_col=None, sampling_rate_hz=None, group_cols=None, edge='rising', nonzero_only=True)
```

## `extract_gazepoint_pdr_signals`

```python
extract_gazepoint_pdr_signals(dat: 'pd.DataFrame', ppg_col: 'str' = 'HRP', time_col: 'str' = 'CNT', group_cols: 'Iterable[str] | None' = None, sampling_rate: 'float | None' = None, min_peak_distance_s: 'float' = 0.3, smooth_window: 'int' = 5, respiration_band=(0.1, 0.6), pdr_resample_rate: 'float' = 4)
```

## `extract_gazepoint_ppg_morphology`

```python
extract_gazepoint_ppg_morphology(data, time_col=None, ppg_col=None, peaks=None, min_peak_distance_s=0.3)
```

## `extract_gazepoint_ppg_templates`

```python
extract_gazepoint_ppg_templates(data, signal_col=None, time_col=None, peaks=None, group_cols=None, sampling_rate_hz=None, before_seconds=0.3, after_seconds=0.6)
```

## `extract_gazepoint_pyhrv_nn_intervals`

```python
extract_gazepoint_pyhrv_nn_intervals(peaks, peak_time_col='peak_time_s', time_unit='seconds')
```

## `extract_gazepoint_respiration_ceemdan`

```python
extract_gazepoint_respiration_ceemdan(dat, signal_col, time_col='CNT', group_cols=None, sampling_rate=None, respiration_band=(0.1, 0.6), scales=(5, 15, 30, 60, 120), external_fun=None)
```

## `extract_gazepoint_scr_recovery_times`

```python
extract_gazepoint_scr_recovery_times(dat, eda_col='GSR_US', time_col='CNT', event_onset_col=None, group_cols=None, pre_onset_baseline_s=2, peak_window_s=5, recovery_window_s=20)
```

## `extract_gazepoint_segments_pspm_style`

```python
extract_gazepoint_segments_pspm_style(data, events, signal_col, time_col=None, event_time_col='onset_time_s', event_id_col=None, condition_col=None, pre_s=1, post_s=5, baseline_window=(-1, 0), baseline_correct=True)
```

## `extract_gazepoint_ttl_events`

```python
extract_gazepoint_ttl_events(data, ttl_columns=None, group_columns=None, validity_column='TTLV', require_validity=True, mode='changes', include_initial=True)
```

## `filter_gazepoint_gaze`

```python
filter_gazepoint_gaze(data, x_col=None, y_col=None, time_col=None, group_cols=None, screen_bounds=(0, 1, 0, 1), max_velocity=inf, drop_invalid=False, suffix='_filtered')
```

## `filter_gazepoint_ibi_implausible`

```python
filter_gazepoint_ibi_implausible(data, ibi_col='IBI', time_col=None, group_cols=None, validity_col=None, unit='auto', min_ibi_ms=300, max_ibi_ms=2000, max_change_ms=400, max_change_prop=0.3, output_col='IBI_clean_ms')
```

## `filter_gazepoint_ppg_butterworth`

```python
filter_gazepoint_ppg_butterworth(x, cutoff_hz=5, sampling_rate_hz=None, passes=1)
```

## `filter_gazepoint_ppg_signal`

```python
filter_gazepoint_ppg_signal(x, sampling_rate_hz, type='lowpass', low_hz=None, high_hz=None, passes=1)
```

## `filter_gazepoint_signal`

```python
filter_gazepoint_signal(data, signal_cols, method='moving_average', group_cols=None, time_col=None, window=5, suffix=None, overwrite=False, na_rm=False)
```

## `fit_gazepoint_convolution_glm`

```python
fit_gazepoint_convolution_glm(data, design, signal_col, time_col=None, design_time_col='time_s', regressor_cols=None)
```

## `flag_gazepoint_artifacts_svm`

```python
flag_gazepoint_artifacts_svm(x, model=None, feature_cols=None, probability_threshold=0.5, **kwargs)
```

## `flag_gazepoint_biometric_dropouts`

```python
flag_gazepoint_biometric_dropouts(data, signal_cols=None, group_cols=None, time_col=None, min_missing_run=5, min_flatline_run=10, constant_tolerance=0, prefix='biometric_dropout')
```

## `flag_gazepoint_hrv_segments`

```python
flag_gazepoint_hrv_segments(data, rr_col=None, time_col=None, group_cols=None, window_s=60, min_beats=20, min_duration_s=20, min_rr_ms=300, max_rr_ms=2000, max_artifact_prop=0.2, max_successive_change_prop=0.2)
```

## `flag_gazepoint_mad_artifacts`

```python
flag_gazepoint_mad_artifacts(dat, eda_col='GSR_US', time_col=None, group_cols=None, mad_multiplier=8, flatline_tolerance=1e-06, flatline_min_run=5, wall_abs_change=None, output_prefix='mad')
```

## `flag_gazepoint_ppg_quality`

```python
flag_gazepoint_ppg_quality(data, time_col=None, ppg_col=None, window_s=10, step_s=None, missing_prop_threshold=0.2, flat_sd_threshold=1e-06, outlier_prop_threshold=0.1)
```

## `flag_gazepoint_rr_outliers`

```python
flag_gazepoint_rr_outliers(rr_intervals, method='mad', z_threshold=5, mad_threshold=5, min_rr=300, max_rr=2000, return_='flags', **kwargs)
```

## `flag_kleckner_eda_artifacts`

```python
flag_kleckner_eda_artifacts(dat, eda_col='GSR_US', time_col=None, group_cols=None, min_us=0.01, max_us=100, max_abs_percent_change_per_second=20, transition_padding=1, output_prefix='kleckner')
```

## `flip_gazepoint_ppg_signal`

```python
flip_gazepoint_ppg_signal(x, method='negative')
```

## `format_gazepoint_biometrics_feature_inventory`

```python
format_gazepoint_biometrics_feature_inventory(inventory=None, include_internal=False, sort=True)
```

## `fuse_gazepoint_respiration_kalman`

```python
fuse_gazepoint_respiration_kalman(dat, primary_col, secondary_col, time_col=None, group_cols=None, process_var=0.01, primary_var=0.05, secondary_var=0.05, output_col='respiration_kalman_fused')
```

## `gazepoint_interoperability_manifest`

```python
gazepoint_interoperability_manifest(include_support=True)
```

## `generate_gazepoint_manifest`

```python
generate_gazepoint_manifest(input_paths=None, parameters=None, outputs=None, notes=None, write_path=None, include_session_info=True)
```

## `get_gazepoint_plot_data`

```python
get_gazepoint_plot_data(plot)
```

## `get_gazepoint_plot_settings`

```python
get_gazepoint_plot_settings(plot)
```

## `gpbiometrics_info`

```python
gpbiometrics_info(print=True, include_session=False)
```

## `import_gazepoint_biometric_folder`

```python
import_gazepoint_biometric_folder(path, pattern='\\.csv$', recursive=False, include_fixations=True, include_all_gaze=True, include_other_csv=False, na=('', 'NA', 'NaN'))
```

## `import_gazepoint_biometrics`

```python
import_gazepoint_biometrics(file, na=('', 'NA', 'NaN'))
```

## `import_gazepoint_data`

```python
import_gazepoint_data(dir, session=None, pattern='\\.csv$', recursive=False, session_match='prefix', file_encoding='UTF-8-BOM', add_file_info=True)
```

## `import_gazepoint_data_summary`

```python
import_gazepoint_data_summary(file)
```

## `import_gazepoint_event_log`

```python
import_gazepoint_event_log(path, time_col=None, event_col=None, id_col=None, sep=None, **kwargs)
```

## `import_gazepoint_lsl_xdf`

```python
import_gazepoint_lsl_xdf(path, stream_name_pattern='Gazepoint|GP3|GSR|EDA|Biometric|TTL|Pupil|Gaze', include_all_streams=False, flatten=True, pyxdf_module='pyxdf')
```

## `import_gazepoint_pyhrv_results`

```python
import_gazepoint_pyhrv_results(path)
```

## `impute_gazepoint_missing`

```python
impute_gazepoint_missing(data, method='linear', cols=None, time_col=None, group_cols=None, max_gap=inf, fill_edges=True, constant_value=0, add_flags=True, treat_infinite_as_missing=True)
```

## `interpolate_gazepoint_pupil_blinks`

```python
interpolate_gazepoint_pupil_blinks(data, pupil_cols=None, time_col=None, blink_col=None, max_gap_s=None, method='linear', suffix='_interp')
```

## `join_gazepoint_biometrics_to_gp3tools`

```python
join_gazepoint_biometrics_to_gp3tools(biometrics, gp3tools_master, *args, **kwargs)
```

## `join_gazepoint_biometrics_to_master`

```python
join_gazepoint_biometrics_to_master(master, biometrics, by, all_x=True)
```

## `match_gazepoint_events_to_biometrics`

```python
match_gazepoint_events_to_biometrics(data, events, pre=0, post=5, time_col=None, event_time_col=None, event_id_col=None, summary_cols=None, return_='windows', **kwargs)
```

## `merge_gazepoint_recordings_pspm_style`

```python
merge_gazepoint_recordings_pspm_style(recordings, time_col=None, gap_seconds=1, recording_col='pspm_recording', reset_first_time=True)
```

## `model_gazepoint_eda_point_process`

```python
model_gazepoint_eda_point_process(dat, eda_col='GSR_US', time_col='CNT', group_cols=None, event_time_col=None, event_indicator_col=None, derivative_mad_multiplier=6, min_event_distance_s=1)
```

## `model_gazepoint_hr_point_process`

```python
model_gazepoint_hr_point_process(dat, ibi_col='IBI', time_col=None, beat_time_col=None, group_cols=None, ibi_units='auto')
```

## `model_gazepoint_hrv_ipfm`

```python
model_gazepoint_hrv_ipfm(dat, ibi_col='IBI', beat_time_col=None, group_cols=None, ibi_units='auto', output_sampling_rate=4, max_frequency=0.5)
```

## `normalize_gazepoint_scr`

```python
normalize_gazepoint_scr(amplitudes, method='z', amplitude_col=None, group_cols=None, output_col='scr_amplitude_normalized', na_rm=True)
```

## `optimize_gazepoint_cvxeda_tau`

```python
optimize_gazepoint_cvxeda_tau(dat, eda_col='GSR_US', time_col='CNT', group_cols=None, tau0_grid=array([2.  , 2.25, 2.5 , 2.75, 3.  , 3.25, 3.5 , 3.75, 4.  ]), tau1=0.7, sampling_rate=None, ridge_lambda=0.01, max_irf_seconds=20)
```

## `pipeline_comparison_dashboard`

```python
pipeline_comparison_dashboard(data, participant_col=None, session_col=None, grouping_cols=None, missingness_col=None, quality_col=None, qc_status_col=None, failed_rules_col=None, excluded_col=None, notes_col=None)
```

## `plot_gazepoint_aoi_biometrics`

```python
plot_gazepoint_aoi_biometrics(x, value_col='mean_value', aoi_col='aoi_label', signal_col='signal', group_col=None, plot_type='boxplot', title=None)
```

## `plot_gazepoint_biometric_quality`

```python
plot_gazepoint_biometric_quality(data, quality_cols=None, signal_cols=None, time_col=None, group_col=None, dropout_prefix='biometric_dropout', max_points=5000, main=None, plot=True, **kwargs)
```

## `plot_gazepoint_biometric_report_dashboard`

```python
plot_gazepoint_biometric_report_dashboard(data=None, signal_activity=None, time_resets=None, signal_cols=None, group_cols=None, time_col=None, include_signal_activity=True, include_time_resets=True, max_groups=30, continue_on_error=True, title_prefix='Gazepoint biometric QC')
```

## `plot_gazepoint_biometric_signals`

```python
plot_gazepoint_biometric_signals(data, signal_cols=None, time_col=None, group_col=None, max_points=5000, standardize=False, type='line', main=None, xlab=None, ylab=None, legend=True, plot=True, **kwargs)
```

## `plot_gazepoint_cluster_null_distribution`

```python
plot_gazepoint_cluster_null_distribution(result, cluster_id=1, observed_mass=None, bins=30)
```

## `plot_gazepoint_cluster_permutation`

```python
plot_gazepoint_cluster_permutation(x, alpha=None, show_all_clusters=False)
```

## `plot_gazepoint_design_coverage`

```python
plot_gazepoint_design_coverage(audit, type='condition_counts')
```

## `plot_gazepoint_eda_decomposition`

```python
plot_gazepoint_eda_decomposition(data, time_col=None, signal_cols=None, group_cols=None, standardise=False, max_points=5000, title=None)
```

## `plot_gazepoint_eda_gram`

```python
plot_gazepoint_eda_gram(dat, eda_col='GSR_US', time_col='CNT', group_cols=None, group_id_to_plot=None, sampling_rate=None, window_seconds=30, step_seconds=5, frequency_range=(0.01, 0.5), frequency_bins=64, log_power=True, plot=True, main='EDA-gram')
```

## `plot_gazepoint_export_profile`

```python
plot_gazepoint_export_profile(profile, type='files', top_n=20)
```

## `plot_gazepoint_missingness`

```python
plot_gazepoint_missingness(data, cols=None, time_col=None, id_col=None, max_points=5000)
```

## `plot_gazepoint_multimodal_timeline`

```python
plot_gazepoint_multimodal_timeline(data, time_col=None, signal_cols=None, group_cols=None, participant_col=None, stimulus_col=None, trial_col=None, event_time_col=None, event_col=None, standardise=True, show_event_markers=True, title=None)
```

## `plot_gazepoint_ppg_breathing`

```python
plot_gazepoint_ppg_breathing(rr_ms, rr_time_s=None, resample_hz=4, breathing_band=(0.1, 0.5))
```

## `plot_gazepoint_ppg_peak_detection`

```python
plot_gazepoint_ppg_peak_detection(detection, group=None, accepted_only=False)
```

## `plot_gazepoint_ppg_poincare`

```python
plot_gazepoint_ppg_poincare(peaks=None, rr_ms=None, group_col='group')
```

## `plot_gazepoint_ppg_segmentwise`

```python
plot_gazepoint_ppg_segmentwise(segmentwise, measure='bpm')
```

## `plot_gazepoint_pyhrv_hr_heatplot`

```python
plot_gazepoint_pyhrv_hr_heatplot(nni_ms, time_bins=20, hr_bins=20)
```

## `plot_gazepoint_pyhrv_radar_chart`

```python
plot_gazepoint_pyhrv_radar_chart(measures, columns=('sdnn', 'rmssd', 'sdsd', 'pnn50', 'lf_norm', 'hf_norm', 'sd1', 'sd2'))
```

## `plot_gazepoint_pyhrv_tachogram`

```python
plot_gazepoint_pyhrv_tachogram(nni_ms, time_s=None)
```

## `plot_gazepoint_saccade_main_sequence`

```python
plot_gazepoint_saccade_main_sequence(dat, amplitude_col=None, peak_velocity_col=None, group_col=None, log_axes=True, add_smoother=True, main='Gazepoint saccade main-sequence diagnostic')
```

## `plot_gazepoint_scr_events`

```python
plot_gazepoint_scr_events(data, scr_peaks, event_windows=None, events=None, time_col=None, signal_col=None, phasic_col=None, group_cols=None, show_events=True, max_points=5000, title=None)
```

## `plot_gazepoint_scr_specification_curve`

```python
plot_gazepoint_scr_specification_curve(x, estimate_col=None, specification_col='specification_id', add_zero_line=True, main='SCR specification curve')
```

## `plot_gazepoint_signal_activity`

```python
plot_gazepoint_signal_activity(data, signal_cols=None, group_cols=None, metric='active_signal', max_groups=30, title=None)
```

## `plot_gazepoint_signal_quality`

```python
plot_gazepoint_signal_quality(quality, metric='prop_missing', x=None, colour=None, facet=None)
```

## `plot_gazepoint_time_resets`

```python
plot_gazepoint_time_resets(data, time_col=None, group_cols=None, max_groups=30, title=None)
```

## `prepare_gazepoint_aoi_biometrics_model_data`

```python
prepare_gazepoint_aoi_biometrics_model_data(x, outcome_col='mean_value', predictor_cols=('aoi_label', 'signal'), factor_cols=('aoi_label', 'signal'), numeric_cols=None, group_cols=None, drop_missing_outcome=True, min_rows=None, standardise_outcome=False, standardise_within='signal')
```

## `prepare_gazepoint_artifact_svm_features`

```python
prepare_gazepoint_artifact_svm_features(dat, eda_col='GSR_US', time_col=None, group_cols=None, segment_seconds=5, samples_per_segment=None, sampling_rate=None)
```

## `prepare_gazepoint_bids_eye`

```python
prepare_gazepoint_bids_eye(data, execute=True, **kwargs)
```

## `prepare_gazepoint_bids_physio`

```python
prepare_gazepoint_bids_physio(data, execute=True, **kwargs)
```

## `prepare_gazepoint_biometrics_lme_data`

```python
prepare_gazepoint_biometrics_lme_data(data, outcome_col, fixed_effect_cols=None, condition_cols=None, covariate_cols=None, random_effect_cols=None, participant_col=None, stimulus_col=None, trial_col=None, window_col=None, baseline_col=None, baseline_correct=False, factor_cols=None, continuous_cols=None, scale_continuous=False, include_window=True, drop_missing=True, min_rows=10)
```

## `prepare_gazepoint_biosppy_input`

```python
prepare_gazepoint_biosppy_input(data, signal_type='auto', signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, missing='error', irregular='error', sampling_tolerance=0.05, min_segment_samples=3, signal_units=None, output_dir=None, prefix='gazepoint_biosppy', write_manifest=True, overwrite=False)
```

## `prepare_gazepoint_ctsi_input`

```python
prepare_gazepoint_ctsi_input(dat, eda_col='GSR_US', time_col='CNT', group_cols=None, event_onset_col=None, event_name_col=None, sampling_rate=None, tau0_range=(2, 4), tau1_range=(0.5, 1), sparsity_grid=(0.001, 0.01, 0.1, 1), output_dir=None, prefix='gazepoint_ctsi')
```

## `prepare_gazepoint_cvxeda_input`

```python
prepare_gazepoint_cvxeda_input(data, **kwargs)
```

## `prepare_gazepoint_eyetrackingr_input`

```python
prepare_gazepoint_eyetrackingr_input(data, participant_col=None, trial_col=None, time_col=None, time_unit='auto', sampling_rate_hz=None, rezero_time=False, trackloss_col=None, validity_col=None, valid_values=None, x_col=None, y_col=None, aoi_col=None, aoi_cols=None, aoi_levels=None, outside_aoi_values=('', 'none', 'no_aoi', 'outside', 'outside_aoi', 'non_aoi', 'background'), allow_aoi_overlap=False, item_cols=None, predictor_cols=None, treat_non_aoi_looks_as_missing=True, sampling_tolerance=0.05, irregular='error', create_object=False)
```

## `prepare_gazepoint_gazer_input`

```python
prepare_gazepoint_gazer_input(data, participant_col=None, trial_col=None, time_col=None, time_unit='auto', sampling_rate_hz=None, rezero_time=False, x_col=None, y_col=None, x_left_col=None, y_left_col=None, x_right_col=None, y_right_col=None, pupil_col=None, pupil_left_col=None, pupil_right_col=None, validity_col=None, validity_left_col=None, validity_right_col=None, valid_values=None, blink_col=None, blink_left_col=None, blink_right_col=None, invalid_coordinate_values=None, invalid_pupil_values=None, mask_invalid=False, other_cols=None, sampling_tolerance=0.05, irregular='error', create_object=False)
```

## `prepare_gazepoint_heartpy_input`

```python
prepare_gazepoint_heartpy_input(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, output_dir=None, prefix='gazepoint_heartpy')
```

## `prepare_gazepoint_ledalab_input`

```python
prepare_gazepoint_ledalab_input(data, **kwargs)
```

## `prepare_gazepoint_mixed_model_data`

```python
prepare_gazepoint_mixed_model_data(data, outcome_cols=None, participant_col=None, trial_col=None, condition_cols=None, factor_cols=None, numeric_cols=None, center_numeric=True, scale_numeric=False, drop_missing_outcomes=True, **kwargs)
```

## `prepare_gazepoint_mne_events`

```python
prepare_gazepoint_mne_events(events, event_time_col=None, event_label_col=None, event_code_col=None, marker_cols=None, participant_col=None, trial_col=None, time_unit='auto', sampling_rate_hz=None, recording_start_s=0, first_samp=0, event_id=None, previous_value=0, marker_onset='change', duplicate='error', export_csv=None)
```

## `prepare_gazepoint_mne_input`

```python
prepare_gazepoint_mne_input(data, channel_cols=None, channel_names=None, channel_types=None, time_col=None, time_unit='auto', sampling_rate_hz=None, first_samp=0, scale_factors=None, missing='error', irregular='error', sampling_tolerance=0.05)
```

## `prepare_gazepoint_multimodal_model_data`

```python
prepare_gazepoint_multimodal_model_data(biometrics, eye_tracking=None, group_columns=None, biometric_is_summarised=False, by=None, all=False)
```

## `prepare_gazepoint_neurokit_eda_input`

```python
prepare_gazepoint_neurokit_eda_input(data, eda_col='GSR_US', time_col=None, group_cols=None, sampling_rate=None, output_dir=None, prefix='gazepoint_neurokit_eda')
```

## `prepare_gazepoint_pspm_dcm_input`

```python
prepare_gazepoint_pspm_dcm_input(dat, eda_col='GSR_US', time_col='CNT', event_onset_col=None, event_duration_col=None, event_name_col=None, participant_col=None, session_col=None, sampling_rate=None, output_dir=None, prefix='gazepoint_pspm_dcm')
```

## `prepare_gazepoint_pspm_input`

```python
prepare_gazepoint_pspm_input(data, **kwargs)
```

## `prepare_gazepoint_pupillometryr_input`

```python
prepare_gazepoint_pupillometryr_input(data, participant_col=None, trial_col=None, time_col=None, condition_col=None, pupil_left_col=None, pupil_right_col=None, pupil_col=None, time_unit='auto', sampling_rate_hz=None, rezero_time=False, invalid_pupil_values=None, validity_cols=None, valid_values=None, blink_cols=None, mask_invalid=False, create_mean_pupil=True, other_cols=None, sampling_tolerance=0.05, irregular='error', create_object=False)
```

## `prepare_gazepoint_pyhrv_input`

```python
prepare_gazepoint_pyhrv_input(data, ibi_col=None, group_cols=None, unit='auto', filter='none', min_nni_ms=300, max_nni_ms=2000, collapse_repeated_intervals=False, repeated_tolerance_ms=1e-08, output_dir=None, prefix='gazepoint_pyhrv', write_manifest=True, overwrite=False)
```

## `prepare_gazepoint_pyppg_input`

```python
prepare_gazepoint_pyppg_input(data, ppg_col=None, time_col=None, group_cols=None, sampling_rate=None, time_unit='auto', min_finite_prop=0.5, output_dir=None, prefix='gazepoint_pyppg')
```

## `prepare_gazepoint_rhrv_input`

```python
prepare_gazepoint_rhrv_input(*args, **kwargs)
```

## `prepare_gazepoint_scr_hurdle_model_data`

```python
prepare_gazepoint_scr_hurdle_model_data(scr_event_windows, response_col='response_flag', amplitude_col='scr_amplitude', latency_col='scr_latency', rise_time_col='scr_rise_time', recovery_time_col='scr_recovery_time', predictor_cols=None, factor_cols=None, numeric_cols=None, group_cols=None, event_id_col='event_id', amplitude_transform='none', amplitude_offset=1e-06, drop_missing_predictors=True)
```

## `prepare_gazepoint_timecourse_test_data`

```python
prepare_gazepoint_timecourse_test_data(data, outcome_col, time_col, condition_col, participant_col, condition_a=None, condition_b=None, time_bin_width=None, aggregation='mean', require_complete=True)
```

## `preprocess_gazepoint_all`

```python
preprocess_gazepoint_all(data, impute_missing=True, clean_pupil=True, filter_gaze=True, max_gap=10, screen_bounds=(0, 1, 0, 1), max_velocity=inf, verbose=True)
```

## `preprocess_gazepoint_scr_pspm_style`

```python
preprocess_gazepoint_scr_pspm_style(data, signal_col=None, time_col=None, sampling_rate_hz=None, range=(0, 50), slope_limit_per_s=10, clipping_tolerance=1e-05, clipping_seconds=0.5, min_valid_island_seconds=1, artifact_epoch_seconds=0.25, smoothing_seconds=0.25)
```

## `process_gazepoint_ppg_heartpy_style`

```python
process_gazepoint_ppg_heartpy_style(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, clean_rr=True, clean_rr_method='quotient', frequency_method='welch', output_dir=None, **kwargs)
```

## `process_gazepoint_ppg_segmentwise`

```python
process_gazepoint_ppg_segmentwise(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, window_seconds=60, overlap=0.5, min_segment_seconds=10, clean_rr=True, clean_rr_method='quotient', frequency_method='welch', **kwargs)
```

## `profile_gazepoint_export_folder`

```python
profile_gazepoint_export_folder(path, pattern='\\.csv$', recursive=False, max_files=inf, max_rows=inf, na_strings=('', 'NA', 'NaN'))
```

## `recommend_gazepoint_biometric_exclusions`

```python
recommend_gazepoint_biometric_exclusions(data, group_columns=None, data_is_window_summary=False, participant_column=None, gsr_min_usable_pct=50, hr_min_usable_pct=50, dial_min_usable_pct=50, require_gsr=True, require_hr=True, require_dial=False)
```

## `reconstruct_gazepoint_ppg_clipping`

```python
reconstruct_gazepoint_ppg_clipping(x, near_max_prop=0.02, flat_diff_prop=0.001, min_run=2)
```

## `regress_gazepoint_pupil_luminance`

```python
regress_gazepoint_pupil_luminance(dat, pupil_col, luminance_col, group_cols=None, time_col=None, output_col='pupil_luminance_adjusted', fitted_col='pupil_luminance_fitted', include_quadratic=True, model_by_group=True, add_intercept_mean=True)
```

## `reject_gazepoint_ppg_peaks`

```python
reject_gazepoint_ppg_peaks(peaks, group_col='group', rr_tolerance=0.3, min_rr_ms=300)
```

## `remove_gazepoint_ppg_baseline_wander`

```python
remove_gazepoint_ppg_baseline_wander(x, sampling_rate_hz, method='median', window_seconds=2)
```

## `report_gazepoint_cluster_permutation`

```python
report_gazepoint_cluster_permutation(result, cluster_alpha=0.05, digits=3, include_assumptions=True)
```

## `report_gazepoint_data_quality`

```python
report_gazepoint_data_quality(data, output_dir=None, report_name='gazepoint_data_quality', formats=('html', 'csv'), max_plot_columns=6, open=False)
```

## `respiration_from_ppg`

```python
respiration_from_ppg(data, **kwargs)
```

## `run_gazepoint_automated_statistics`

```python
run_gazepoint_automated_statistics(dat, outcome_cols, group_col, alpha=0.05, p_adjust_method='holm', normality_alpha=0.05, min_group_n=3)
```

## `run_gazepoint_biometrics_real_data_readiness`

```python
run_gazepoint_biometrics_real_data_readiness(data=None, workflow_result=None, min_rows=100, min_active_signal_count=1, max_missing_prop=0.5, required_signal_cols=None, require_gsr_us_preferred=True, require_ibi_for_hrv=False, time_col=None, ttl_cols=None)
```

## `run_gazepoint_biometrics_workflow`

```python
run_gazepoint_biometrics_workflow(path, group_columns=None, recursive=False, include_fixations=False, include_all_gaze=True, include_other_csv=False, require_active_signal=True, create_exclusion_recommendations=True, gsr_min_usable_pct=50, hr_min_usable_pct=50, dial_min_usable_pct=50, extract_ttl_events=True, ttl_event_mode='changes', audit_sampling=True, sampling_group_columns=None, sampling_time_column=None, sampling_time_unit='samples', expected_sampling_rate_hz=60)
```

## `run_gazepoint_biosppy_eda`

```python
run_gazepoint_biosppy_eda(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, smoothing_seconds=4)
```

## `run_gazepoint_biosppy_ppg`

```python
run_gazepoint_biosppy_ppg(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None)
```

## `run_gazepoint_cluster_permutation`

```python
run_gazepoint_cluster_permutation(data, outcome_col='value', time_col='time', condition_col='condition', participant_col='participant', design='within', condition_a=None, condition_b=None, n_permutations=1000, cluster_forming_alpha=0.05, cluster_alpha=0.05, tail='two.sided', seed=None, time_bin_width=None, aggregation='mean')
```

## `run_gazepoint_cluster_permutation_anova`

```python
run_gazepoint_cluster_permutation_anova(*args, **kwargs)
```

## `run_gazepoint_cluster_permutation_covariate_adjusted`

```python
run_gazepoint_cluster_permutation_covariate_adjusted(*args, **kwargs)
```

## `run_gazepoint_cluster_permutation_lmer`

```python
run_gazepoint_cluster_permutation_lmer(*args, **kwargs)
```

## `run_gazepoint_cluster_permutation_parallel`

```python
run_gazepoint_cluster_permutation_parallel(*args, **kwargs)
```

## `run_gazepoint_cluster_threshold_sensitivity`

```python
run_gazepoint_cluster_threshold_sensitivity(data, dv, time, condition, subject, thresholds=(0.01, 0.025, 0.05, 0.1), cluster_alpha=0.05, seed=None, **kwargs)
```

## `run_gazepoint_eda_analysis_pipeline`

```python
run_gazepoint_eda_analysis_pipeline(data=None, path=None, eda_col=None, time_col=None, group_cols=None, signal_cols=None, sampling_rate=None, baseline_window=None, event_windows=None, event_data=None, lag_signal_pair=None, convert_resistance_to_us=False, prepare_external_bridges=True, bridge_methods=('neurokit', 'cvxeda', 'ledalab', 'pspm'), prepare_model_data=True, create_reports=True, output_dir=None, prefix='gazepoint_eda_pipeline', continue_on_error=True)
```

## `run_gazepoint_heartpy_crosscheck`

```python
run_gazepoint_heartpy_crosscheck(data, signal_col=None, time_col=None, group_cols=None, sampling_rate_hz=None, **kwargs)
```

## `run_gazepoint_multidimensional_cluster_permutation`

```python
run_gazepoint_multidimensional_cluster_permutation(*args, **kwargs)
```

## `run_gazepoint_neurokit_eda_crosscheck`

```python
run_gazepoint_neurokit_eda_crosscheck(data, eda_col='GSR_US', time_col=None, group_cols=None, sampling_rate=None, execute=False, python='python', output_dir=None, prefix='gazepoint_neurokit_crosscheck', keep_files=False)
```

## `run_gazepoint_online_design_optimization`

```python
run_gazepoint_online_design_optimization(candidate_table, condition_col='condition', utility_col='expected_utility', block_col=None, cost_col=None, previous_assignments=None, exploration_weight=0.1, balance_weight=0.1, maximise=True)
```

## `run_gazepoint_pyhrv_style`

```python
run_gazepoint_pyhrv_style(nni_ms=None, peaks=None, peak_time_col='peak_time_s', time_unit='seconds', frequency_method='welch')
```

## `run_gazepoint_real_data_smoke`

```python
run_gazepoint_real_data_smoke(data_dir='', output_dir=None, dataset_mode='subdirectories', pattern='\\.csv$', recursive=True, workflow_args=None, diagnostic_args=None, workflow_runner=None, summary_runner=None, diagnostic_runner=None, stop_on_error=False, write_results=False, overwrite=False, protect_repository=True)
```

## `run_gazepoint_scr_multiverse`

```python
run_gazepoint_scr_multiverse(dat, signal_col='GSR_US', time_col='time', trial_cols=None, condition_col=None, participant_col=None, event_time_col=None, latency_windows=((1, 3), (1, 4), (1, 5)), thresholds=(0.01, 0.05), baseline_methods=('median', 'mean'), baseline_window=(-1, 0), response_metrics=('max_minus_baseline',), model_function=None)
```

## `run_gazepoint_scr_threshold_sensitivity`

```python
run_gazepoint_scr_threshold_sensitivity(data, phasic_col=None, signal_col=None, time_col=None, group_cols=None, amplitude_min_values=(0.005, 0.01, 0.02, 0.03), min_peak_distance_values=(1, 5, 10, 20, 30), recovery_fraction=0.5, smooth_width=1, events=None, event_time_col=None, event_id_col=None, event_label_col=None, ttl_cols=None, ttl_valid_col=None, event_detection='rising', analysis_window=(0, 6), response_window=(1, 4), peak_selection='largest_amplitude', collapse_simultaneous_events=False, include_event_windows=True, keep_objects=False)
```

## `run_gazepoint_tfce`

```python
run_gazepoint_tfce(*args, **kwargs)
```

## `run_gpbiometrics_shiny`

```python
run_gpbiometrics_shiny()
```

## `run_gpbiometrics_shiny_annotator`

```python
run_gpbiometrics_shiny_annotator()
```

## `scale_gazepoint_ppg_sections`

```python
scale_gazepoint_ppg_sections(data, signal_col=None, section_cols=None, method='zscore', output_col='ppg_scaled', range=(0, 1))
```

## `scale_gazepoint_ppg_signal`

```python
scale_gazepoint_ppg_signal(x, method='zscore', range=(0, 1))
```

## `screen_gazepoint_eda_nonresponders`

```python
screen_gazepoint_eda_nonresponders(x, group_cols=None, response_col='response_flag', amplitude_col='scr_amplitude', min_events=1, min_response_events=1, min_response_rate=0.05, min_detected_peaks=1)
```

## `segment_gazepoint_pyhrv_nni`

```python
segment_gazepoint_pyhrv_nni(nni_ms, segment_seconds=300, overlap=0, min_intervals=3)
```

## `session_info_gazepoint`

```python
session_info_gazepoint(packages=None, include_loaded=True, timestamp=None)
```

## `simulate_gazepoint_artifact`

```python
simulate_gazepoint_artifact(data, signal_cols, artifact=('missing_run', 'flatline', 'spike'), n_artifacts=1, artifact_length=5, magnitude=None, seed=None, suffix='_artifact', overwrite=False)
```

## `simulate_gazepoint_biometrics`

```python
simulate_gazepoint_biometrics(n_seconds=120, sampling_rate=60, participant_id='sim_p1', scr_onsets=None, scr_rate_per_min=4, pulse_rate_bpm=72, respiration_rate_bpm=15, eda_noise_sd=0.01, ppg_noise_sd=0.02, include_ttl=True, seed=None)
```

## `simulate_gazepoint_cluster_timecourse_data`

```python
simulate_gazepoint_cluster_timecourse_data(n_subjects=12, n_time=60, conditions=('A', 'B'), effect_start=25, effect_end=38, effect_size=0.6, noise_sd=0.4, subject_sd=0.25, time_start=1, time_step=1, effect_condition='B', seed=None)
```

## `simulate_gazepoint_eye_data`

```python
simulate_gazepoint_eye_data(params=None)
```

## `simulate_gazepoint_multimodal_data`

```python
simulate_gazepoint_multimodal_data(n=None, duration_s=20, sampling_rate_hz=50, seed=1, participant='P01', n_trials=4)
```

## `smooth_gazepoint_biometrics`

```python
smooth_gazepoint_biometrics(data, value_column, window=5, output_column=None, na_rm=True)
```

## `smooth_gazepoint_ppg_signal`

```python
smooth_gazepoint_ppg_signal(x, sampling_rate_hz, method='mean', window_seconds=0.1)
```

## `smooth_gazepoint_pupil`

```python
smooth_gazepoint_pupil(data, pupil_cols=None, id_cols=None, window=5, suffix='_smooth', min_nonmissing=1)
```

## `split_gazepoint_sessions_pspm_style`

```python
split_gazepoint_sessions_pspm_style(data, time_col=None, gap_seconds=None, session_col='pspm_session', reset_time=True)
```

## `standardise_gazepoint_adaptive_ema`

```python
standardise_gazepoint_adaptive_ema(dat, signal_col='GSR_US', group_cols=None, time_col=None, alpha=0.05, iqr_multiplier=1.5, suffix='_adaptive_ema', center_suffix='_ema_center', scale_suffix='_ema_scale', min_scale=1e-08, overwrite=False)
```

## `standardise_gazepoint_biometric_names`

```python
standardise_gazepoint_biometric_names(data, style='canonical', rename=True)
```

## `standardise_gazepoint_biometrics_within_unit`

```python
standardise_gazepoint_biometrics_within_unit(*args, **kwargs)
```

## `standardise_gazepoint_plot_contract`

```python
standardise_gazepoint_plot_contract(plot, plot_data=None, settings=None, interpretation_notes=None, plot_type=None)
```

## `standardise_gazepoint_range_correction`

```python
standardise_gazepoint_range_correction(dat, signal_col, group_col='source_participant', suffix='_Range_Corrected', min_valid=2, zero_range_action='NA', overwrite=False)
```

## `standardise_gazepoint_zscore`

```python
standardise_gazepoint_zscore(dat, signal_col='SCR_Amplitude', group_col='source_participant', suffix='_Z', min_valid=2, overwrite=False)
```

## `standardize_gazepoint_adaptive_ema`

```python
standardize_gazepoint_adaptive_ema(*args, **kwargs)
```

## `standardize_gazepoint_biometrics_within_unit`

```python
standardize_gazepoint_biometrics_within_unit(data, signal_cols=None, unit_cols=None, reference_col=None, reference_value=True, suffix='_z_within', center=True, scale=True, min_valid=2, zero_sd_action='NA', overwrite=False)
```

## `standardize_gazepoint_column_names`

```python
standardize_gazepoint_column_names(data, dictionary=None, conflict='suffix', ignore_case=True)
```

## `standardize_gazepoint_columns`

```python
standardize_gazepoint_columns(data, **kwargs)
```

## `standardize_gazepoint_plot_contracts`

```python
standardize_gazepoint_plot_contracts(plot, plot_data=None, settings=None, interpretation_notes=None, plot_type=None)
```

## `standardize_gazepoint_range_correction`

```python
standardize_gazepoint_range_correction(*args, **kwargs)
```

## `standardize_gazepoint_zscore`

```python
standardize_gazepoint_zscore(*args, **kwargs)
```

## `summarise_gazepoint_aoi_biometrics`

```python
summarise_gazepoint_aoi_biometrics(data, aoi_col='AOI', signal_cols=None, group_cols=None, time_col=None, valid_aoi_values=None, drop_missing_aoi=True, min_rows=1)
```

## `summarise_gazepoint_biometric_validity`

```python
summarise_gazepoint_biometric_validity(data, signal_cols=None, validity_cols=None, group_cols=None, active_min_unique=2)
```

## `summarise_gazepoint_biometrics_feature_inventory`

```python
summarise_gazepoint_biometrics_feature_inventory(formatted_inventory=None)
```

## `summarise_gazepoint_biometrics_workflow`

```python
summarise_gazepoint_biometrics_workflow(workflow)
```

## `summarise_gazepoint_decision_log`

```python
summarise_gazepoint_decision_log(log)
```

## `summarise_gazepoint_dial_windows`

```python
summarise_gazepoint_dial_windows(data, *args, dial_col=None, **kwargs)
```

## `summarise_gazepoint_engagement_windows`

```python
summarise_gazepoint_engagement_windows(data, group_columns=None, value_column='DIAL', validity_column='DIALV', exclude_zero=False)
```

## `summarise_gazepoint_fixations_by_aoi`

```python
summarise_gazepoint_fixations_by_aoi(fixations, aoi_col=None, participant_col=None, trial_col=None, group_cols=None, start_col=None, end_col=None, duration_col=None, event_onset_col=None, time_unit='auto', duration_unit='auto', sampling_rate_hz=None, include_unassigned=False, unassigned_label='UNASSIGNED')
```

## `summarise_gazepoint_full_biometric_windows`

```python
summarise_gazepoint_full_biometric_windows(data, group_columns, include_ibi_hrv=True)
```

## `summarise_gazepoint_gsr_tonic_phasic`

```python
summarise_gazepoint_gsr_tonic_phasic(data, gsr_col=None, group_cols=None, time_col=None, window_n=15, peak_threshold=None, output_prefix='gsr')
```

## `summarise_gazepoint_gsr_windows`

```python
summarise_gazepoint_gsr_windows(data, group_columns=None, value_column=None, validity_column='GSRV', exclude_zero=True)
```

## `summarise_gazepoint_hr_windows`

```python
summarise_gazepoint_hr_windows(data, group_columns=None, value_column='HR', validity_column='HRV', exclude_zero=True)
```

## `summarise_gazepoint_hrv_features`

```python
summarise_gazepoint_hrv_features(data, ibi_col=None, group_cols=None, time_col=None, ibi_unit='auto', min_ibi_ms=300, max_ibi_ms=2000, min_valid_ibi=3)
```

## `summarise_gazepoint_ibi_hrv_windows`

```python
summarise_gazepoint_ibi_hrv_windows(data, group_columns, ibi_column='IBI', validity_column='HRV', min_ibi=0.3, max_ibi=2.0)
```

## `summarise_gazepoint_ibi_windows`

```python
summarise_gazepoint_ibi_windows(data, ibi_col=None, group_cols=None, time_col=None, unit='auto', min_ibi_ms=300, max_ibi_ms=2000, max_jump_ms=500, exclude_large_jumps=True, min_valid_ibi=2)
```

## `summarise_gazepoint_multimodal_windows`

```python
summarise_gazepoint_multimodal_windows(data, group_columns=None, exclude_zero=True)
```

## `summarise_gazepoint_scr_event_windows`

```python
summarise_gazepoint_scr_event_windows(data=None, scr_peaks=None, events=None, time_col=None, event_time_col=None, event_id_col=None, event_label_col=None, group_cols=None, ttl_cols=None, ttl_valid_col=None, event_detection='rising', analysis_window=(0, 6), response_window=(1, 4), amplitude_col='amplitude', peak_time_col='peak_time', onset_time_col='onset_time', rise_time_col='rise_time', recovery_time_col='recovery_time_after_peak', peak_status_col='status', peak_selection='largest_amplitude', collapse_simultaneous_events=False)
```

## `summarize_gazepoint_aoi_dwell`

```python
summarize_gazepoint_aoi_dwell(data, time_col=None, aoi_col=None, duration_col=None, group_cols=None, valid_col=None)
```

## `summarize_gazepoint_audit_trail`

```python
summarize_gazepoint_audit_trail(audit_index, by=None)
```

## `summarize_gazepoint_beat_corrections`

```python
summarize_gazepoint_beat_corrections(correction, by=None)
```

## `summarize_gazepoint_eventlocked_multimodal`

```python
summarize_gazepoint_eventlocked_multimodal(data, events, time_col=None, event_time_col=None, event_id_col=None, group_cols=None, signal_cols=None, pre_s=1, post_s=3, baseline_window_s=(-1, 0), summary_window_s=(0, 3))
```

## `summarize_gazepoint_export_inventory`

```python
summarize_gazepoint_export_inventory(path, recursive=True)
```

## `summarize_gazepoint_feature_coverage`

```python
summarize_gazepoint_feature_coverage(path='.', exports=None, patterns=None)
```

## `summarize_gazepoint_fixations`

```python
summarize_gazepoint_fixations(fixDF, duration_col=None, x_col=None, y_col=None, participant_col=None, trial_col=None, aoi_col=None, group_cols=None, duration_unit='auto')
```

## `summarize_gazepoint_fixations_by_aoi`

```python
summarize_gazepoint_fixations_by_aoi(*args, **kwargs)
```

## `summarize_gazepoint_missingness`

```python
summarize_gazepoint_missingness(data, signal_cols=None, time_col=None, group_cols=None, long_gap_s=None, count_nonfinite=True)
```

## `summarize_gazepoint_nonwear`

```python
summarize_gazepoint_nonwear(nonwear, by='signal')
```

## `summarize_gazepoint_preregistration_readiness`

```python
summarize_gazepoint_preregistration_readiness(audit, by=None)
```

## `summarize_gazepoint_pupil_events`

```python
summarize_gazepoint_pupil_events(data, events, pre=1, post=3, time_col=None, pupil_col=None, event_time_col=None, event_id_col=None, baseline_window=None, response_window=(0, 3))
```

## `summarize_gazepoint_qc_overview`

```python
summarize_gazepoint_qc_overview(data, group_cols=None, quality_index_col=None, flag_cols=None, metric_cols=None)
```

## `summarize_gazepoint_scanpath_metrics`

```python
summarize_gazepoint_scanpath_metrics(data, x_col=None, y_col=None, time_col=None, aoi_col=None, fixation_id_col=None, group_cols=None, min_saccade_distance=0.02)
```

## `summarize_gazepoint_scr_recovery`

```python
summarize_gazepoint_scr_recovery(data, events, pre=1, post=6, time_col=None, signal_col=None, event_time_col=None, event_id_col=None, baseline_window=None, peak_window=(0.5, 4), recovery_fraction=0.5)
```

## `summarize_gazepoint_signal_quality`

```python
summarize_gazepoint_signal_quality(quality, by='signal')
```

## `summarize_gazepoint_time_clusters`

```python
summarize_gazepoint_time_clusters(x, alpha=None)
```

## `summarize_gazepoint_tracking`

```python
summarize_gazepoint_tracking(data, pupil_cols=None, x_col=None, y_col=None, group_cols=None, screen_bounds=(0, 1, 0, 1), nonpositive_is_invalid=True)
```

## `sync_gazepoint_biometrics_with_gaze`

```python
sync_gazepoint_biometrics_with_gaze(biometrics, gaze, by, all_x=True, suffixes=('.gaze', '.bio'))
```

## `sync_gazepoint_signals_via_lsl`

```python
sync_gazepoint_signals_via_lsl(streams, reference=None, time_cols=None, clock_offsets_s=None, known_lags_s=None, relative_zero='reference', dejitter='none', nominal_rates_hz=None, merge='none', tolerance_s=None)
```

## `test_gazepoint_hrv_nonlinearity`

```python
test_gazepoint_hrv_nonlinearity(dat, ibi_col='IBI', group_cols=None, metric='sample_entropy', n_surrogates=99, surrogate_method='phase_randomized', m=2, r_multiplier=0.2, statistic_fun=None, seed=None)
```

## `trim_gazepoint_biometrics_pspm_style`

```python
trim_gazepoint_biometrics_pspm_style(data, start_s=None, end_s=None, time_col=None, reset_time=False)
```

## `upsample_gazepoint_data`

```python
upsample_gazepoint_data(data, time_col, signal_cols=None, group_cols=None, interval=None, method='linear')
```

## `validate_gazepoint_biometrics`

```python
validate_gazepoint_biometrics(data, require_active_signal=False)
```

## `validate_gazepoint_format`

```python
validate_gazepoint_format(data, required_cols=None, optional_cols=None, expected_modalities=None, standardize=False, strict=False, **kwargs)
```

## `validate_gazepoint_gaze`

```python
validate_gazepoint_gaze(data, time_col=None, x_col=None, y_col=None, validity_cols=None, group_cols=None, coordinate_system='auto', screen_width_px=None, screen_height_px=None, time_unit='auto', sampling_rate_hz=None, expected_sampling_rate_hz=None, sampling_tolerance=0.2, missing_threshold=0.2, gap_multiplier=3)
```

## `validate_gazepoint_metadata`

```python
validate_gazepoint_metadata(data, required_cols=(), expected_cols=(), id_cols=None, time_col=None, unique_cols=None, allow_missing_ids=False)
```

## `write_gazepoint_biometrics_report_tables`

```python
write_gazepoint_biometrics_report_tables(tables, output_dir, prefix='gazepoint_biometrics', overwrite=True, include_empty_message_tables=False)
```

## `write_gazepoint_decision_log`

```python
write_gazepoint_decision_log(log, path, summary_path=None, overwrite=False)
```

## `write_gazepoint_export_profile`

```python
write_gazepoint_export_profile(profile, path, prefix='gazepoint_export_profile', overwrite=False)
```

## `write_gazepoint_interoperability_audit`

```python
write_gazepoint_interoperability_audit(x, output_dir, prefix='gpbiometrics-interoperability', overwrite=False)
```

## `write_gazepoint_mne_fif`

```python
write_gazepoint_mne_fif(x, fname, events=None, overwrite=False, fmt='single', python=None, execute=True, keep_intermediate=False, verbose=False, **kwargs)
```

## `write_gazepoint_real_data_smoke`

```python
write_gazepoint_real_data_smoke(x, output_dir, prefix='gpbiometrics-real-data-smoke', overwrite=False, protect_repository=True)
```
