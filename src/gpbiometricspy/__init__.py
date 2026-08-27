from __future__ import annotations

from ._types import ParityNotImplementedError, ReportText
from .physiology_qc import compute_gazepoint_scr_latency, compute_gazepoint_signal_lag_matrix, estimate_gazepoint_respiration_from_ppg, flag_gazepoint_hrv_segments
from .pupil_gaze import clean_gazepoint_pupil_signal, detect_gazepoint_pupil_blinks, filter_gazepoint_gaze, summarize_gazepoint_fixations
from .pupil_qc import detect_gazepoint_blinks, plot_gazepoint_missingness, smooth_gazepoint_pupil, validate_gazepoint_metadata
from .reports import create_gazepoint_audit_report_section, create_gazepoint_methods_section, create_gazepoint_qc_supplement, create_gazepoint_reproducibility_statement

from .user_workflows import (
    plot_gazepoint_biometric_signals,
    plot_gazepoint_biometric_quality,
    plot_gazepoint_signal_activity,
    plot_gazepoint_time_resets,
    plot_gazepoint_biometric_report_dashboard,
    plot_gazepoint_eda_decomposition,
    plot_gazepoint_scr_events,
    plot_gazepoint_multimodal_timeline,
    plot_gazepoint_scr_specification_curve,
    create_gazepoint_biometrics_feature_inventory,
    format_gazepoint_biometrics_feature_inventory,
    summarise_gazepoint_biometrics_feature_inventory,
    summarise_gazepoint_full_biometric_windows,
    prepare_gazepoint_multimodal_model_data,
    prepare_gazepoint_biometrics_lme_data,
    summarise_gazepoint_dial_windows,
    join_gazepoint_biometrics_to_gp3tools,
    run_gazepoint_biometrics_real_data_readiness,
    run_gazepoint_biometrics_workflow,
    diagnose_gazepoint_biometrics_workflow,
    summarise_gazepoint_biometrics_workflow,
    create_gazepoint_biometrics_report_tables,
    write_gazepoint_biometrics_report_tables,
    export_gazepoint_biometrics_report_bundle,
    create_gazepoint_biometrics_report,
)
from .signal_quality import classify_gazepoint_signal_quality, compute_gazepoint_signal_quality, plot_gazepoint_signal_quality, summarize_gazepoint_signal_quality
from .aoi_biometrics import summarise_gazepoint_aoi_biometrics, prepare_gazepoint_aoi_biometrics_model_data, plot_gazepoint_aoi_biometrics
from .alignment_aoi import align_gazepoint_streams_by_events, build_gazepoint_aoi_timecourse, summarize_gazepoint_eventlocked_multimodal, create_gazepoint_quality_dashboard
from .compatibility import (
    standardize_gazepoint_column_names, standardize_gazepoint_columns,
    validate_gazepoint_format, interpolate_gazepoint_pupil_blinks,
    clean_gazepoint_pupil, respiration_from_ppg, prepare_gazepoint_mixed_model_data,
)
from .schema_io import (
    import_gazepoint_data_summary, standardise_gazepoint_biometric_names,
    detect_gazepoint_time_columns, detect_gazepoint_biometric_timebase,
    detect_gazepoint_biometric_schema,
)
from .frontdoor import (
    import_gazepoint_biometrics, import_gazepoint_biometric_folder,
    check_gazepoint_biometric_columns, detect_active_biometric_channels,
    validate_gazepoint_biometrics, audit_gazepoint_biometric_missingness,
)
from .intake_alignment import (
    extract_gazepoint_ttl_events, align_gazepoint_biometrics_to_ttl,
    sync_gazepoint_biometrics_with_gaze, join_gazepoint_biometrics_to_master,
    chunk_gazepoint_biometrics,
)
from .data_io_cleaning import import_gazepoint_data, impute_gazepoint_missing
from .qc_dropouts import (audit_gazepoint_time_resets, audit_gazepoint_signal_activity, flag_gazepoint_biometric_dropouts, detect_gazepoint_nonwear, summarize_gazepoint_nonwear, filter_gazepoint_signal, upsample_gazepoint_data)
from .event_frontdoor import (epoch_gazepoint_scr, normalize_gazepoint_scr, flag_gazepoint_rr_outliers, compute_gazepoint_engagement_index, summarize_gazepoint_missingness, detrend_gazepoint_signal, audit_gazepoint_biometrics_file)
from .validity import summarise_gazepoint_biometric_validity
from .qc_windows_standardization import (standardise_gazepoint_zscore, standardize_gazepoint_zscore, standardise_gazepoint_range_correction, standardize_gazepoint_range_correction, audit_gazepoint_gsr_quality, audit_gazepoint_hr_quality, audit_gazepoint_engagement_dial, summarise_gazepoint_gsr_windows, summarise_gazepoint_hr_windows, summarise_gazepoint_engagement_windows, summarise_gazepoint_multimodal_windows)
from .governance_extra import (create_gazepoint_preregistration_checklist, audit_gazepoint_preregistration_consistency, summarize_gazepoint_preregistration_readiness, gazepoint_interoperability_manifest, audit_gazepoint_interoperability_versions, write_gazepoint_interoperability_audit)
from .governance_core import (create_gazepoint_analysis_decision_log, add_gazepoint_decision, summarise_gazepoint_decision_log, write_gazepoint_decision_log, create_gazepoint_pipeline_map, audit_gazepoint_pipeline_steps, export_gazepoint_pipeline_dot, create_gazepoint_audit_index, summarize_gazepoint_audit_trail, export_gazepoint_audit_trail_markdown, summarize_gazepoint_export_inventory, audit_gazepoint_dataset_structure, create_gazepoint_sidecar_template)
from .release_profile import (audit_gazepoint_release_readiness, summarize_gazepoint_feature_coverage, create_gazepoint_release_checklist, profile_gazepoint_export_folder, compare_gazepoint_export_profiles, write_gazepoint_export_profile, plot_gazepoint_export_profile)
from .qc_audits_design import (audit_gazepoint_beats, correct_gazepoint_beats, summarize_gazepoint_beat_corrections, compute_gazepoint_quality_index, audit_gazepoint_session_comparability, summarize_gazepoint_qc_overview, audit_gazepoint_experiment_design, audit_gazepoint_event_coverage, audit_gazepoint_condition_balance, plot_gazepoint_design_coverage)



from .final_remaining import (
    assign_gazepoint_aoi, audit_gazepoint_smoke_privacy, check_gazepoint_bids,
    create_gazepoint_preregistration_template, create_gazepoint_trial_regressors,
    denoise_gazepoint_eda_autoencoder, denoise_gazepoint_ppg_autoencoder,
    detect_gazepoint_fixations, detect_gazepoint_saccades, export_gazepoint_to_bids,
    flag_gazepoint_artifacts_svm, model_gazepoint_eda_point_process, model_gazepoint_hr_point_process,
    pipeline_comparison_dashboard, prepare_gazepoint_artifact_svm_features,
    prepare_gazepoint_eyetrackingr_input, prepare_gazepoint_gazer_input, prepare_gazepoint_pupillometryr_input,
    preprocess_gazepoint_all, report_gazepoint_data_quality, run_gazepoint_real_data_smoke,
    run_gpbiometrics_shiny, run_gpbiometrics_shiny_annotator, write_gazepoint_real_data_smoke,
)

from .final_science_bridges import (
    analyze_gazepoint_ac_susceptance, run_gazepoint_automated_statistics,
    analyze_gazepoint_cardiorespiratory_causality, compare_gazepoint_conditions_bootstrap,
    prepare_gazepoint_ctsi_input, optimize_gazepoint_cvxeda_tau,
    create_gazepoint_eda_analysis_pipeline, run_gazepoint_eda_analysis_pipeline,
    import_gazepoint_lsl_xdf, run_gazepoint_online_design_optimization,
    prepare_gazepoint_pspm_dcm_input, run_gazepoint_scr_multiverse,
)

from .final_deterministic import (
    standardise_gazepoint_adaptive_ema, standardize_gazepoint_adaptive_ema,
    audit_gazepoint_gsr_units, downsample_gazepoint_data,
    audit_gazepoint_biometric_sampling, summarise_gazepoint_hrv_features,
    summarise_gazepoint_ibi_hrv_windows, recommend_gazepoint_biometric_exclusions,
    baseline_correct_gazepoint_pupil, plot_gazepoint_saccade_main_sequence,
    simulate_gazepoint_eye_data, simulate_gazepoint_biometrics,
)

from .remaining_core import (
    simulate_gazepoint_artifact, generate_gazepoint_manifest, create_gazepoint_dictionary, anonymize_gazepoint_data,
    baseline_correct_gazepoint_gsr, baseline_correct_gazepoint_hr, smooth_gazepoint_biometrics,
    filter_gazepoint_ibi_implausible, compare_gazepoint_hr_ibi_consistency, extract_gazepoint_hrv_features,
)

from .roadmap_helpers import (
    compute_gazepoint_scr_habituation, summarize_gazepoint_scr_recovery,
    summarize_gazepoint_pupil_events, summarize_gazepoint_tracking,
    audit_gazepoint_pupil_luminance, extract_gazepoint_ppg_morphology,
    flag_gazepoint_ppg_quality, import_gazepoint_event_log,
    match_gazepoint_events_to_biometrics, assert_gazepoint_columns,
    gpbiometrics_info, audit_gazepoint_export_schema,
    simulate_gazepoint_multimodal_data, assess_gazepoint_sampling_irregularity,
    diagnose_gazepoint_sync_drift, summarize_gazepoint_aoi_dwell,
    summarize_gazepoint_scanpath_metrics, create_gazepoint_analysis_manifest,
    compute_gazepoint_ppg_template_similarity, compute_gazepoint_hrv_wavelet_psd,
)

from .roadmap_final_gaps import (
    validate_gazepoint_gaze, summarise_gazepoint_fixations_by_aoi,
    summarize_gazepoint_fixations_by_aoi, prepare_gazepoint_bids_eye,
    prepare_gazepoint_bids_physio, write_gazepoint_mne_fif,
    estimate_gazepoint_lsl_clock_offsets,
)

from .advanced_physiology import (
    correct_gazepoint_eda_temperature, extract_gazepoint_beats_kmeans,
    audit_gazepoint_stabilization_period, regress_gazepoint_pupil_luminance,
    model_gazepoint_hrv_ipfm, prepare_gazepoint_ledalab_input,
    prepare_gazepoint_pspm_input, prepare_gazepoint_cvxeda_input,
    classify_gazepoint_eda_response_pattern, extract_gazepoint_bilateral_eda_asymmetry,
    denoise_gazepoint_quantization_noise, extract_gazepoint_edr_pca,
    analyze_gazepoint_skin_potential,
)
from .pspm_style import (
    extract_gazepoint_markerinfo_pspm_style, combine_gazepoint_marker_channels_pspm_style,
    trim_gazepoint_biometrics_pspm_style, split_gazepoint_sessions_pspm_style,
    merge_gazepoint_recordings_pspm_style, preprocess_gazepoint_scr_pspm_style,
    extract_gazepoint_segments_pspm_style, create_gazepoint_pspm_glm_design,
    fit_gazepoint_convolution_glm, export_gazepoint_pspm_model_estimates,
)

from .biosppy_style import (
    prepare_gazepoint_biosppy_input, extract_gazepoint_eda_events_biosppy_style,
    estimate_gazepoint_eda_recovery_times, run_gazepoint_biosppy_eda,
    detect_gazepoint_ppg_onsets, extract_gazepoint_ppg_templates, run_gazepoint_biosppy_ppg,
    detrend_gazepoint_rri_window, correct_gazepoint_rri_artifacts_local,
    compute_gazepoint_signal_power_spectrum, compute_gazepoint_signal_band_power,
    compute_gazepoint_signal_phase_locking, compute_gazepoint_signal_correlation,
)

from .cluster_permutation import (
    prepare_gazepoint_timecourse_test_data, run_gazepoint_cluster_permutation,
    summarize_gazepoint_time_clusters, plot_gazepoint_cluster_permutation,
    audit_gazepoint_timecourse_grid, diagnose_gazepoint_cluster_design,
    plot_gazepoint_cluster_null_distribution, report_gazepoint_cluster_permutation,
    run_gazepoint_cluster_threshold_sensitivity, simulate_gazepoint_cluster_timecourse_data,
    export_gazepoint_cluster_results, run_gazepoint_cluster_permutation_anova,
    run_gazepoint_cluster_permutation_lmer, run_gazepoint_tfce,
    run_gazepoint_multidimensional_cluster_permutation, estimate_gazepoint_cluster_onset,
    estimate_gazepoint_cluster_offset, run_gazepoint_cluster_permutation_covariate_adjusted,
    run_gazepoint_cluster_permutation_parallel, export_gazepoint_mne_cluster_input,
    export_gazepoint_permuco_cluster_input, export_gazepoint_permutes_cluster_input,
)

from .mne_eeg_lsl import (
    prepare_gazepoint_mne_events, prepare_gazepoint_mne_input, align_gazepoint_to_eeg,
    create_gazepoint_eye_methods_text, session_info_gazepoint, sync_gazepoint_signals_via_lsl,
)

from .pyhrv_style import (
    prepare_gazepoint_pyhrv_input, extract_gazepoint_pyhrv_nn_intervals,
    compute_gazepoint_pyhrv_nn_diff, compute_gazepoint_pyhrv_heart_rate,
    create_gazepoint_pyhrv_time_vector, check_gazepoint_pyhrv_interval,
    segment_gazepoint_pyhrv_nni, compute_gazepoint_pyhrv_nni_parameters,
    compute_gazepoint_pyhrv_nni_differences_parameters, compute_gazepoint_pyhrv_hr_parameters,
    compute_gazepoint_pyhrv_sdnn, compute_gazepoint_pyhrv_sdnn_index,
    compute_gazepoint_pyhrv_sdann, compute_gazepoint_pyhrv_rmssd,
    compute_gazepoint_pyhrv_sdsd, compute_gazepoint_pyhrv_nnxx,
    compute_gazepoint_pyhrv_nn50, compute_gazepoint_pyhrv_nn20,
    compute_gazepoint_pyhrv_triangular_index, compute_gazepoint_pyhrv_tinn,
    compute_gazepoint_pyhrv_time_domain, compute_gazepoint_pyhrv_welch_psd,
    compute_gazepoint_pyhrv_lomb_psd, compute_gazepoint_pyhrv_ar_psd,
    compute_gazepoint_pyhrv_frequency_domain, compare_gazepoint_pyhrv_psd_methods,
    compute_gazepoint_pyhrv_psd_waterfall, compute_gazepoint_pyhrv_poincare,
    compute_gazepoint_pyhrv_sample_entropy, compute_gazepoint_pyhrv_dfa,
    compute_gazepoint_pyhrv_nonlinear, plot_gazepoint_pyhrv_tachogram,
    plot_gazepoint_pyhrv_hr_heatplot, plot_gazepoint_pyhrv_radar_chart,
    export_gazepoint_pyhrv_results, import_gazepoint_pyhrv_results,
    run_gazepoint_pyhrv_style,
)

from .heartpy_style import (
    prepare_gazepoint_heartpy_input, export_gazepoint_heartpy_input,
    reconstruct_gazepoint_ppg_clipping, enhance_gazepoint_ppg_peaks,
    filter_gazepoint_ppg_butterworth, correct_gazepoint_ppg_hampel,
    detect_gazepoint_ppg_peaks, reject_gazepoint_ppg_peaks,
    compute_gazepoint_ppg_measures, estimate_gazepoint_breathing_rate_from_ibi,
    plot_gazepoint_ppg_peak_detection, create_gazepoint_heartpy_report,
    run_gazepoint_heartpy_crosscheck, estimate_gazepoint_samplerate_mstimer,
    estimate_gazepoint_samplerate_datetime, scale_gazepoint_ppg_signal,
    scale_gazepoint_ppg_sections, flip_gazepoint_ppg_signal,
    remove_gazepoint_ppg_baseline_wander, smooth_gazepoint_ppg_signal,
    filter_gazepoint_ppg_signal, clean_gazepoint_rr_intervals,
    compute_gazepoint_ppg_frequency_measures, process_gazepoint_ppg_heartpy_style,
    process_gazepoint_ppg_segmentwise, plot_gazepoint_ppg_segmentwise,
    plot_gazepoint_ppg_poincare, plot_gazepoint_ppg_breathing,
    check_gazepoint_ppg_binary_quality,
)

from .scientific_qc import (
    audit_gazepoint_ibi_quality, summarise_gazepoint_ibi_windows,
    classify_gazepoint_scr_intervals, flag_kleckner_eda_artifacts,
    convert_gazepoint_gsr_to_conductance, summarise_gazepoint_gsr_tonic_phasic,
)

R_EXPORTS = ['add_gazepoint_decision', 'align_gazepoint_biometrics_to_ttl', 'align_gazepoint_streams_by_events', 'align_gazepoint_to_eeg', 'analyze_gazepoint_ac_susceptance', 'analyze_gazepoint_cardiorespiratory_causality', 'analyze_gazepoint_skin_potential', 'anonymize_gazepoint_data', 'assert_gazepoint_columns', 'assess_gazepoint_hrp_waveform_quality', 'assess_gazepoint_sampling_irregularity', 'assign_gazepoint_aoi', 'audit_gazepoint_beats', 'audit_gazepoint_biometric_missingness', 'audit_gazepoint_biometric_sampling', 'audit_gazepoint_biometric_sync_drift', 'audit_gazepoint_biometrics_file', 'audit_gazepoint_condition_balance', 'audit_gazepoint_dataset_structure', 'audit_gazepoint_distributional_drift', 'audit_gazepoint_eda_artifacts', 'audit_gazepoint_engagement_dial', 'audit_gazepoint_event_coverage', 'audit_gazepoint_experiment_design', 'audit_gazepoint_export_schema', 'audit_gazepoint_gsr_quality', 'audit_gazepoint_gsr_units', 'audit_gazepoint_hr_quality', 'audit_gazepoint_ibi_quality', 'audit_gazepoint_interoperability_versions', 'audit_gazepoint_pipeline_steps', 'audit_gazepoint_preregistration_consistency', 'audit_gazepoint_pupil_luminance', 'audit_gazepoint_release_readiness', 'audit_gazepoint_session_comparability', 'audit_gazepoint_signal_activity', 'audit_gazepoint_smoke_privacy', 'audit_gazepoint_stabilization_period', 'audit_gazepoint_time_resets', 'audit_gazepoint_timecourse_grid', 'baseline_correct_gazepoint_gsr', 'baseline_correct_gazepoint_hr', 'baseline_correct_gazepoint_pupil', 'build_gazepoint_aoi_timecourse', 'calculate_gazepoint_rsa', 'check_gazepoint_bids', 'check_gazepoint_biometric_columns', 'check_gazepoint_plot_contract', 'check_gazepoint_ppg_binary_quality', 'check_gazepoint_pyhrv_interval', 'chunk_gazepoint_biometrics', 'classify_gazepoint_eda_response_pattern', 'classify_gazepoint_scr_intervals', 'classify_gazepoint_signal_quality', 'clean_gazepoint_pupil', 'clean_gazepoint_pupil_signal', 'clean_gazepoint_rr_intervals', 'combine_gazepoint_marker_channels_pspm_style', 'compare_gazepoint_conditions_bootstrap', 'compare_gazepoint_export_profiles', 'compare_gazepoint_hr_ibi_consistency', 'compare_gazepoint_pyhrv_psd_methods', 'compute_gazepoint_engagement_index', 'compute_gazepoint_hrv_wavelet_psd', 'compute_gazepoint_ppg_frequency_measures', 'compute_gazepoint_ppg_measures', 'compute_gazepoint_ppg_template_similarity', 'compute_gazepoint_pyhrv_ar_psd', 'compute_gazepoint_pyhrv_dfa', 'compute_gazepoint_pyhrv_frequency_domain', 'compute_gazepoint_pyhrv_heart_rate', 'compute_gazepoint_pyhrv_hr_parameters', 'compute_gazepoint_pyhrv_lomb_psd', 'compute_gazepoint_pyhrv_nn20', 'compute_gazepoint_pyhrv_nn50', 'compute_gazepoint_pyhrv_nn_diff', 'compute_gazepoint_pyhrv_nni_differences_parameters', 'compute_gazepoint_pyhrv_nni_parameters', 'compute_gazepoint_pyhrv_nnxx', 'compute_gazepoint_pyhrv_nonlinear', 'compute_gazepoint_pyhrv_poincare', 'compute_gazepoint_pyhrv_psd_waterfall', 'compute_gazepoint_pyhrv_rmssd', 'compute_gazepoint_pyhrv_sample_entropy', 'compute_gazepoint_pyhrv_sdann', 'compute_gazepoint_pyhrv_sdnn', 'compute_gazepoint_pyhrv_sdnn_index', 'compute_gazepoint_pyhrv_sdsd', 'compute_gazepoint_pyhrv_time_domain', 'compute_gazepoint_pyhrv_tinn', 'compute_gazepoint_pyhrv_triangular_index', 'compute_gazepoint_pyhrv_welch_psd', 'compute_gazepoint_quality_index', 'compute_gazepoint_scr_habituation', 'compute_gazepoint_scr_latency', 'compute_gazepoint_signal_band_power', 'compute_gazepoint_signal_correlation', 'compute_gazepoint_signal_lag_matrix', 'compute_gazepoint_signal_phase_locking', 'compute_gazepoint_signal_power_spectrum', 'compute_gazepoint_signal_quality', 'convert_gazepoint_gsr_to_conductance', 'correct_gazepoint_beats', 'correct_gazepoint_eda_temperature', 'correct_gazepoint_ppg_hampel', 'correct_gazepoint_rri_artifacts_local', 'create_gazepoint_analysis_decision_log', 'create_gazepoint_analysis_manifest', 'create_gazepoint_audit_index', 'create_gazepoint_audit_report_section', 'create_gazepoint_biometrics_checklist', 'create_gazepoint_biometrics_feature_inventory', 'create_gazepoint_biometrics_methods_text', 'create_gazepoint_biometrics_report', 'create_gazepoint_biometrics_report_tables', 'create_gazepoint_dictionary', 'create_gazepoint_eda_analysis_pipeline', 'create_gazepoint_eye_methods_text', 'create_gazepoint_heartpy_report', 'create_gazepoint_methods_section', 'create_gazepoint_pipeline_map', 'create_gazepoint_preregistration_checklist', 'create_gazepoint_preregistration_template', 'create_gazepoint_pspm_glm_design', 'create_gazepoint_pyhrv_time_vector', 'create_gazepoint_qc_supplement', 'create_gazepoint_quality_dashboard', 'create_gazepoint_release_checklist', 'create_gazepoint_reproducibility_statement', 'create_gazepoint_sidecar_template', 'create_gazepoint_trial_regressors', 'decompose_gazepoint_eda', 'denoise_gazepoint_eda_autoencoder', 'denoise_gazepoint_eda_wavelet', 'denoise_gazepoint_ppg_autoencoder', 'denoise_gazepoint_quantization_noise', 'detect_active_biometric_channels', 'detect_gazepoint_biometric_schema', 'detect_gazepoint_biometric_timebase', 'detect_gazepoint_blinks', 'detect_gazepoint_doubly_stochastic_changepoints', 'detect_gazepoint_fixations', 'detect_gazepoint_nonwear', 'detect_gazepoint_ppg_onsets', 'detect_gazepoint_ppg_peaks', 'detect_gazepoint_pupil_blinks', 'detect_gazepoint_saccades', 'detect_gazepoint_scr_events', 'detect_gazepoint_scr_peaks', 'detect_gazepoint_time_columns', 'detrend_gazepoint_rri_window', 'detrend_gazepoint_signal', 'diagnose_gazepoint_biometrics_workflow', 'diagnose_gazepoint_cluster_design', 'diagnose_gazepoint_sync_drift', 'downsample_gazepoint_data', 'enhance_gazepoint_ppg_peaks', 'epoch_gazepoint_scr', 'estimate_gazepoint_breathing_rate_from_ibi', 'estimate_gazepoint_cluster_offset', 'estimate_gazepoint_cluster_onset', 'estimate_gazepoint_eda_recovery_times', 'estimate_gazepoint_lsl_clock_offsets', 'estimate_gazepoint_respiration_from_ppg', 'estimate_gazepoint_samplerate_datetime', 'estimate_gazepoint_samplerate_mstimer', 'estimate_gazepoint_signal_lag', 'export_gazepoint_audit_trail_markdown', 'export_gazepoint_biometrics_report_bundle', 'export_gazepoint_cluster_results', 'export_gazepoint_heartpy_input', 'export_gazepoint_mne_cluster_input', 'export_gazepoint_permuco_cluster_input', 'export_gazepoint_permutes_cluster_input', 'export_gazepoint_pipeline_dot', 'export_gazepoint_pspm_model_estimates', 'export_gazepoint_pyhrv_results', 'export_gazepoint_rhrv_input', 'export_gazepoint_to_bids', 'extract_gazepoint_beats_kmeans', 'extract_gazepoint_bilateral_eda_asymmetry', 'extract_gazepoint_eda_complexity', 'extract_gazepoint_eda_events_biosppy_style', 'extract_gazepoint_eda_spectral_power', 'extract_gazepoint_eda_tvsymp', 'extract_gazepoint_edr_pca', 'extract_gazepoint_hrv_asymmetry', 'extract_gazepoint_hrv_features', 'extract_gazepoint_hrv_fragmentation', 'extract_gazepoint_hrv_fuzzy_csi', 'extract_gazepoint_hrv_geometric', 'extract_gazepoint_hrv_nonlinear', 'extract_gazepoint_hrv_rcmse', 'extract_gazepoint_hrv_rqa', 'extract_gazepoint_markerinfo_pspm_style', 'extract_gazepoint_pdr_signals', 'extract_gazepoint_ppg_morphology', 'extract_gazepoint_ppg_templates', 'extract_gazepoint_pyhrv_nn_intervals', 'extract_gazepoint_respiration_ceemdan', 'extract_gazepoint_scr_recovery_times', 'extract_gazepoint_segments_pspm_style', 'extract_gazepoint_ttl_events', 'filter_gazepoint_gaze', 'filter_gazepoint_ibi_implausible', 'filter_gazepoint_ppg_butterworth', 'filter_gazepoint_ppg_signal', 'filter_gazepoint_signal', 'fit_gazepoint_convolution_glm', 'flag_gazepoint_artifacts_svm', 'flag_gazepoint_biometric_dropouts', 'flag_gazepoint_hrv_segments', 'flag_gazepoint_mad_artifacts', 'flag_gazepoint_ppg_quality', 'flag_gazepoint_rr_outliers', 'flag_kleckner_eda_artifacts', 'flip_gazepoint_ppg_signal', 'format_gazepoint_biometrics_feature_inventory', 'fuse_gazepoint_respiration_kalman', 'gazepoint_interoperability_manifest', 'generate_gazepoint_manifest', 'get_gazepoint_plot_data', 'get_gazepoint_plot_settings', 'gpbiometrics_info', 'import_gazepoint_biometric_folder', 'import_gazepoint_biometrics', 'import_gazepoint_data', 'import_gazepoint_data_summary', 'import_gazepoint_event_log', 'import_gazepoint_lsl_xdf', 'import_gazepoint_pyhrv_results', 'impute_gazepoint_missing', 'interpolate_gazepoint_pupil_blinks', 'join_gazepoint_biometrics_to_gp3tools', 'join_gazepoint_biometrics_to_master', 'match_gazepoint_events_to_biometrics', 'merge_gazepoint_recordings_pspm_style', 'model_gazepoint_eda_point_process', 'model_gazepoint_hr_point_process', 'model_gazepoint_hrv_ipfm', 'normalize_gazepoint_scr', 'optimize_gazepoint_cvxeda_tau', 'pipeline_comparison_dashboard', 'plot_gazepoint_aoi_biometrics', 'plot_gazepoint_biometric_quality', 'plot_gazepoint_biometric_report_dashboard', 'plot_gazepoint_biometric_signals', 'plot_gazepoint_cluster_null_distribution', 'plot_gazepoint_cluster_permutation', 'plot_gazepoint_design_coverage', 'plot_gazepoint_eda_decomposition', 'plot_gazepoint_eda_gram', 'plot_gazepoint_export_profile', 'plot_gazepoint_missingness', 'plot_gazepoint_multimodal_timeline', 'plot_gazepoint_ppg_breathing', 'plot_gazepoint_ppg_peak_detection', 'plot_gazepoint_ppg_poincare', 'plot_gazepoint_ppg_segmentwise', 'plot_gazepoint_pyhrv_hr_heatplot', 'plot_gazepoint_pyhrv_radar_chart', 'plot_gazepoint_pyhrv_tachogram', 'plot_gazepoint_saccade_main_sequence', 'plot_gazepoint_scr_events', 'plot_gazepoint_scr_specification_curve', 'plot_gazepoint_signal_activity', 'plot_gazepoint_signal_quality', 'plot_gazepoint_time_resets', 'prepare_gazepoint_aoi_biometrics_model_data', 'prepare_gazepoint_artifact_svm_features', 'prepare_gazepoint_bids_eye', 'prepare_gazepoint_bids_physio', 'prepare_gazepoint_biometrics_lme_data', 'prepare_gazepoint_biosppy_input', 'prepare_gazepoint_ctsi_input', 'prepare_gazepoint_cvxeda_input', 'prepare_gazepoint_eyetrackingr_input', 'prepare_gazepoint_gazer_input', 'prepare_gazepoint_heartpy_input', 'prepare_gazepoint_ledalab_input', 'prepare_gazepoint_mixed_model_data', 'prepare_gazepoint_mne_events', 'prepare_gazepoint_mne_input', 'prepare_gazepoint_multimodal_model_data', 'prepare_gazepoint_neurokit_eda_input', 'prepare_gazepoint_pspm_dcm_input', 'prepare_gazepoint_pspm_input', 'prepare_gazepoint_pupillometryr_input', 'prepare_gazepoint_pyhrv_input', 'prepare_gazepoint_pyppg_input', 'prepare_gazepoint_rhrv_input', 'prepare_gazepoint_scr_hurdle_model_data', 'prepare_gazepoint_timecourse_test_data', 'preprocess_gazepoint_all', 'preprocess_gazepoint_scr_pspm_style', 'process_gazepoint_ppg_heartpy_style', 'process_gazepoint_ppg_segmentwise', 'profile_gazepoint_export_folder', 'recommend_gazepoint_biometric_exclusions', 'reconstruct_gazepoint_ppg_clipping', 'regress_gazepoint_pupil_luminance', 'reject_gazepoint_ppg_peaks', 'remove_gazepoint_ppg_baseline_wander', 'report_gazepoint_cluster_permutation', 'report_gazepoint_data_quality', 'respiration_from_ppg', 'run_gazepoint_automated_statistics', 'run_gazepoint_biometrics_real_data_readiness', 'run_gazepoint_biometrics_workflow', 'run_gazepoint_biosppy_eda', 'run_gazepoint_biosppy_ppg', 'run_gazepoint_cluster_permutation', 'run_gazepoint_cluster_permutation_anova', 'run_gazepoint_cluster_permutation_covariate_adjusted', 'run_gazepoint_cluster_permutation_lmer', 'run_gazepoint_cluster_permutation_parallel', 'run_gazepoint_cluster_threshold_sensitivity', 'run_gazepoint_eda_analysis_pipeline', 'run_gazepoint_heartpy_crosscheck', 'run_gazepoint_multidimensional_cluster_permutation', 'run_gazepoint_neurokit_eda_crosscheck', 'run_gazepoint_online_design_optimization', 'run_gazepoint_pyhrv_style', 'run_gazepoint_real_data_smoke', 'run_gazepoint_scr_multiverse', 'run_gazepoint_scr_threshold_sensitivity', 'run_gazepoint_tfce', 'run_gpbiometrics_shiny', 'run_gpbiometrics_shiny_annotator', 'scale_gazepoint_ppg_sections', 'scale_gazepoint_ppg_signal', 'screen_gazepoint_eda_nonresponders', 'segment_gazepoint_pyhrv_nni', 'session_info_gazepoint', 'simulate_gazepoint_artifact', 'simulate_gazepoint_biometrics', 'simulate_gazepoint_cluster_timecourse_data', 'simulate_gazepoint_eye_data', 'simulate_gazepoint_multimodal_data', 'smooth_gazepoint_biometrics', 'smooth_gazepoint_ppg_signal', 'smooth_gazepoint_pupil', 'split_gazepoint_sessions_pspm_style', 'standardise_gazepoint_adaptive_ema', 'standardise_gazepoint_biometric_names', 'standardise_gazepoint_biometrics_within_unit', 'standardise_gazepoint_plot_contract', 'standardise_gazepoint_range_correction', 'standardise_gazepoint_zscore', 'standardize_gazepoint_adaptive_ema', 'standardize_gazepoint_biometrics_within_unit', 'standardize_gazepoint_column_names', 'standardize_gazepoint_columns', 'standardize_gazepoint_plot_contracts', 'standardize_gazepoint_range_correction', 'standardize_gazepoint_zscore', 'summarise_gazepoint_aoi_biometrics', 'summarise_gazepoint_biometric_validity', 'summarise_gazepoint_biometrics_feature_inventory', 'summarise_gazepoint_biometrics_workflow', 'summarise_gazepoint_decision_log', 'summarise_gazepoint_dial_windows', 'summarise_gazepoint_engagement_windows', 'summarise_gazepoint_fixations_by_aoi', 'summarise_gazepoint_full_biometric_windows', 'summarise_gazepoint_gsr_tonic_phasic', 'summarise_gazepoint_gsr_windows', 'summarise_gazepoint_hr_windows', 'summarise_gazepoint_hrv_features', 'summarise_gazepoint_ibi_hrv_windows', 'summarise_gazepoint_ibi_windows', 'summarise_gazepoint_multimodal_windows', 'summarise_gazepoint_scr_event_windows', 'summarize_gazepoint_aoi_dwell', 'summarize_gazepoint_audit_trail', 'summarize_gazepoint_beat_corrections', 'summarize_gazepoint_eventlocked_multimodal', 'summarize_gazepoint_export_inventory', 'summarize_gazepoint_feature_coverage', 'summarize_gazepoint_fixations', 'summarize_gazepoint_fixations_by_aoi', 'summarize_gazepoint_missingness', 'summarize_gazepoint_nonwear', 'summarize_gazepoint_preregistration_readiness', 'summarize_gazepoint_pupil_events', 'summarize_gazepoint_qc_overview', 'summarize_gazepoint_scanpath_metrics', 'summarize_gazepoint_scr_recovery', 'summarize_gazepoint_signal_quality', 'summarize_gazepoint_time_clusters', 'summarize_gazepoint_tracking', 'sync_gazepoint_biometrics_with_gaze', 'sync_gazepoint_signals_via_lsl', 'test_gazepoint_hrv_nonlinearity', 'trim_gazepoint_biometrics_pspm_style', 'upsample_gazepoint_data', 'validate_gazepoint_biometrics', 'validate_gazepoint_format', 'validate_gazepoint_gaze', 'validate_gazepoint_metadata', 'write_gazepoint_biometrics_report_tables', 'write_gazepoint_decision_log', 'write_gazepoint_export_profile', 'write_gazepoint_interoperability_audit', 'write_gazepoint_mne_fif', 'write_gazepoint_real_data_smoke']

from .advanced_nonlinear import (
    extract_gazepoint_hrv_nonlinear, extract_gazepoint_eda_complexity,
    extract_gazepoint_hrv_fragmentation, extract_gazepoint_hrv_asymmetry,
    extract_gazepoint_hrv_rqa, extract_gazepoint_hrv_geometric,
    extract_gazepoint_pdr_signals, calculate_gazepoint_rsa,
)

from .deterministic_extensions import (
    standardise_gazepoint_plot_contract, check_gazepoint_plot_contract, get_gazepoint_plot_data,
    get_gazepoint_plot_settings, standardize_gazepoint_plot_contracts, export_gazepoint_rhrv_input,
    prepare_gazepoint_rhrv_input, prepare_gazepoint_neurokit_eda_input, run_gazepoint_neurokit_eda_crosscheck,
    standardize_gazepoint_biometrics_within_unit, standardise_gazepoint_biometrics_within_unit,
    estimate_gazepoint_signal_lag, audit_gazepoint_biometric_sync_drift, prepare_gazepoint_pyppg_input,
    assess_gazepoint_hrp_waveform_quality, decompose_gazepoint_eda, detect_gazepoint_scr_events,
    create_gazepoint_biometrics_checklist, create_gazepoint_biometrics_methods_text,
)
from .endgame_science import (
    audit_gazepoint_eda_artifacts, detect_gazepoint_scr_peaks,
    summarise_gazepoint_scr_event_windows, screen_gazepoint_eda_nonresponders,
    prepare_gazepoint_scr_hurdle_model_data, run_gazepoint_scr_threshold_sensitivity,
    extract_gazepoint_eda_spectral_power, denoise_gazepoint_eda_wavelet,
    extract_gazepoint_eda_tvsymp, plot_gazepoint_eda_gram,
    extract_gazepoint_hrv_fuzzy_csi, extract_gazepoint_hrv_rcmse,
    test_gazepoint_hrv_nonlinearity, extract_gazepoint_respiration_ceemdan,
    fuse_gazepoint_respiration_kalman, flag_gazepoint_mad_artifacts,
    audit_gazepoint_distributional_drift, detect_gazepoint_doubly_stochastic_changepoints,
    extract_gazepoint_scr_recovery_times,
)

IMPLEMENTED_EXPORTS = ['add_gazepoint_decision', 'align_gazepoint_biometrics_to_ttl', 'align_gazepoint_streams_by_events', 'analyze_gazepoint_skin_potential', 'anonymize_gazepoint_data', 'assert_gazepoint_columns', 'assess_gazepoint_sampling_irregularity', 'audit_gazepoint_beats', 'audit_gazepoint_biometric_missingness', 'audit_gazepoint_biometrics_file', 'audit_gazepoint_condition_balance', 'audit_gazepoint_dataset_structure', 'audit_gazepoint_engagement_dial', 'audit_gazepoint_event_coverage', 'audit_gazepoint_experiment_design', 'audit_gazepoint_export_schema', 'audit_gazepoint_gsr_quality', 'audit_gazepoint_hr_quality', 'audit_gazepoint_interoperability_versions', 'audit_gazepoint_pipeline_steps', 'audit_gazepoint_preregistration_consistency', 'audit_gazepoint_pupil_luminance', 'audit_gazepoint_release_readiness', 'audit_gazepoint_session_comparability', 'audit_gazepoint_signal_activity', 'audit_gazepoint_stabilization_period', 'audit_gazepoint_time_resets', 'baseline_correct_gazepoint_gsr', 'baseline_correct_gazepoint_hr', 'build_gazepoint_aoi_timecourse', 'check_gazepoint_biometric_columns', 'chunk_gazepoint_biometrics', 'classify_gazepoint_eda_response_pattern', 'classify_gazepoint_signal_quality', 'clean_gazepoint_pupil', 'clean_gazepoint_pupil_signal', 'compare_gazepoint_export_profiles', 'compare_gazepoint_hr_ibi_consistency', 'compute_gazepoint_engagement_index', 'compute_gazepoint_hrv_wavelet_psd', 'compute_gazepoint_ppg_template_similarity', 'compute_gazepoint_quality_index', 'compute_gazepoint_scr_habituation', 'compute_gazepoint_scr_latency', 'compute_gazepoint_signal_lag_matrix', 'compute_gazepoint_signal_quality', 'correct_gazepoint_beats', 'correct_gazepoint_eda_temperature', 'create_gazepoint_analysis_decision_log', 'create_gazepoint_analysis_manifest', 'create_gazepoint_audit_index', 'create_gazepoint_audit_report_section', 'create_gazepoint_dictionary', 'create_gazepoint_methods_section', 'create_gazepoint_pipeline_map', 'create_gazepoint_preregistration_checklist', 'create_gazepoint_qc_supplement', 'create_gazepoint_quality_dashboard', 'create_gazepoint_release_checklist', 'create_gazepoint_reproducibility_statement', 'create_gazepoint_sidecar_template', 'denoise_gazepoint_quantization_noise', 'detect_active_biometric_channels', 'detect_gazepoint_biometric_schema', 'detect_gazepoint_biometric_timebase', 'detect_gazepoint_blinks', 'detect_gazepoint_nonwear', 'detect_gazepoint_pupil_blinks', 'detect_gazepoint_time_columns', 'detrend_gazepoint_signal', 'diagnose_gazepoint_sync_drift', 'epoch_gazepoint_scr', 'estimate_gazepoint_lsl_clock_offsets', 'estimate_gazepoint_respiration_from_ppg', 'export_gazepoint_audit_trail_markdown', 'export_gazepoint_pipeline_dot', 'extract_gazepoint_beats_kmeans', 'extract_gazepoint_bilateral_eda_asymmetry', 'extract_gazepoint_edr_pca', 'extract_gazepoint_hrv_features', 'extract_gazepoint_ppg_morphology', 'extract_gazepoint_ttl_events', 'filter_gazepoint_gaze', 'filter_gazepoint_ibi_implausible', 'filter_gazepoint_signal', 'flag_gazepoint_biometric_dropouts', 'flag_gazepoint_hrv_segments', 'flag_gazepoint_ppg_quality', 'flag_gazepoint_rr_outliers', 'gazepoint_interoperability_manifest', 'generate_gazepoint_manifest', 'gpbiometrics_info', 'import_gazepoint_biometric_folder', 'import_gazepoint_biometrics', 'import_gazepoint_data', 'import_gazepoint_data_summary', 'import_gazepoint_event_log', 'impute_gazepoint_missing', 'interpolate_gazepoint_pupil_blinks', 'join_gazepoint_biometrics_to_master', 'match_gazepoint_events_to_biometrics', 'model_gazepoint_hrv_ipfm', 'normalize_gazepoint_scr', 'plot_gazepoint_aoi_biometrics', 'plot_gazepoint_design_coverage', 'plot_gazepoint_export_profile', 'plot_gazepoint_missingness', 'plot_gazepoint_signal_quality', 'prepare_gazepoint_aoi_biometrics_model_data', 'prepare_gazepoint_bids_eye', 'prepare_gazepoint_bids_physio', 'prepare_gazepoint_cvxeda_input', 'prepare_gazepoint_ledalab_input', 'prepare_gazepoint_mixed_model_data', 'prepare_gazepoint_pspm_input', 'profile_gazepoint_export_folder', 'regress_gazepoint_pupil_luminance', 'respiration_from_ppg', 'simulate_gazepoint_artifact', 'simulate_gazepoint_multimodal_data', 'smooth_gazepoint_biometrics', 'smooth_gazepoint_pupil', 'standardise_gazepoint_biometric_names', 'standardise_gazepoint_range_correction', 'standardise_gazepoint_zscore', 'standardize_gazepoint_column_names', 'standardize_gazepoint_columns', 'standardize_gazepoint_range_correction', 'standardize_gazepoint_zscore', 'summarise_gazepoint_aoi_biometrics', 'summarise_gazepoint_biometric_validity', 'summarise_gazepoint_decision_log', 'summarise_gazepoint_engagement_windows', 'summarise_gazepoint_fixations_by_aoi', 'summarise_gazepoint_gsr_windows', 'summarise_gazepoint_hr_windows', 'summarise_gazepoint_multimodal_windows', 'summarize_gazepoint_aoi_dwell', 'summarize_gazepoint_audit_trail', 'summarize_gazepoint_beat_corrections', 'summarize_gazepoint_eventlocked_multimodal', 'summarize_gazepoint_export_inventory', 'summarize_gazepoint_feature_coverage', 'summarize_gazepoint_fixations', 'summarize_gazepoint_fixations_by_aoi', 'summarize_gazepoint_missingness', 'summarize_gazepoint_nonwear', 'summarize_gazepoint_preregistration_readiness', 'summarize_gazepoint_pupil_events', 'summarize_gazepoint_qc_overview', 'summarize_gazepoint_scanpath_metrics', 'summarize_gazepoint_scr_recovery', 'summarize_gazepoint_signal_quality', 'summarize_gazepoint_tracking', 'sync_gazepoint_biometrics_with_gaze', 'upsample_gazepoint_data', 'validate_gazepoint_biometrics', 'validate_gazepoint_format', 'validate_gazepoint_gaze', 'validate_gazepoint_metadata', 'write_gazepoint_decision_log', 'write_gazepoint_export_profile', 'write_gazepoint_interoperability_audit', 'write_gazepoint_mne_fif']
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['extract_gazepoint_markerinfo_pspm_style', 'combine_gazepoint_marker_channels_pspm_style', 'trim_gazepoint_biometrics_pspm_style', 'split_gazepoint_sessions_pspm_style', 'merge_gazepoint_recordings_pspm_style', 'preprocess_gazepoint_scr_pspm_style', 'extract_gazepoint_segments_pspm_style', 'create_gazepoint_pspm_glm_design', 'fit_gazepoint_convolution_glm', 'export_gazepoint_pspm_model_estimates']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['prepare_gazepoint_biosppy_input', 'extract_gazepoint_eda_events_biosppy_style', 'estimate_gazepoint_eda_recovery_times', 'run_gazepoint_biosppy_eda', 'detect_gazepoint_ppg_onsets', 'extract_gazepoint_ppg_templates', 'run_gazepoint_biosppy_ppg', 'detrend_gazepoint_rri_window', 'correct_gazepoint_rri_artifacts_local', 'compute_gazepoint_signal_power_spectrum', 'compute_gazepoint_signal_band_power', 'compute_gazepoint_signal_phase_locking', 'compute_gazepoint_signal_correlation']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['prepare_gazepoint_timecourse_test_data', 'run_gazepoint_cluster_permutation', 'summarize_gazepoint_time_clusters', 'plot_gazepoint_cluster_permutation', 'audit_gazepoint_timecourse_grid', 'diagnose_gazepoint_cluster_design', 'plot_gazepoint_cluster_null_distribution', 'report_gazepoint_cluster_permutation', 'run_gazepoint_cluster_threshold_sensitivity', 'simulate_gazepoint_cluster_timecourse_data', 'export_gazepoint_cluster_results', 'run_gazepoint_cluster_permutation_anova', 'run_gazepoint_cluster_permutation_lmer', 'run_gazepoint_tfce', 'run_gazepoint_multidimensional_cluster_permutation', 'estimate_gazepoint_cluster_onset', 'estimate_gazepoint_cluster_offset', 'run_gazepoint_cluster_permutation_covariate_adjusted', 'run_gazepoint_cluster_permutation_parallel', 'export_gazepoint_mne_cluster_input', 'export_gazepoint_permuco_cluster_input', 'export_gazepoint_permutes_cluster_input']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['prepare_gazepoint_mne_events', 'prepare_gazepoint_mne_input', 'align_gazepoint_to_eeg', 'create_gazepoint_eye_methods_text', 'session_info_gazepoint', 'sync_gazepoint_signals_via_lsl']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['prepare_gazepoint_pyhrv_input', 'extract_gazepoint_pyhrv_nn_intervals', 'compute_gazepoint_pyhrv_nn_diff', 'compute_gazepoint_pyhrv_heart_rate', 'create_gazepoint_pyhrv_time_vector', 'check_gazepoint_pyhrv_interval', 'segment_gazepoint_pyhrv_nni', 'compute_gazepoint_pyhrv_nni_parameters', 'compute_gazepoint_pyhrv_nni_differences_parameters', 'compute_gazepoint_pyhrv_hr_parameters', 'compute_gazepoint_pyhrv_sdnn', 'compute_gazepoint_pyhrv_sdnn_index', 'compute_gazepoint_pyhrv_sdann', 'compute_gazepoint_pyhrv_rmssd', 'compute_gazepoint_pyhrv_sdsd', 'compute_gazepoint_pyhrv_nnxx', 'compute_gazepoint_pyhrv_nn50', 'compute_gazepoint_pyhrv_nn20', 'compute_gazepoint_pyhrv_triangular_index', 'compute_gazepoint_pyhrv_tinn', 'compute_gazepoint_pyhrv_time_domain', 'compute_gazepoint_pyhrv_welch_psd', 'compute_gazepoint_pyhrv_lomb_psd', 'compute_gazepoint_pyhrv_ar_psd', 'compute_gazepoint_pyhrv_frequency_domain', 'compare_gazepoint_pyhrv_psd_methods', 'compute_gazepoint_pyhrv_psd_waterfall', 'compute_gazepoint_pyhrv_poincare', 'compute_gazepoint_pyhrv_sample_entropy', 'compute_gazepoint_pyhrv_dfa', 'compute_gazepoint_pyhrv_nonlinear', 'plot_gazepoint_pyhrv_tachogram', 'plot_gazepoint_pyhrv_hr_heatplot', 'plot_gazepoint_pyhrv_radar_chart', 'export_gazepoint_pyhrv_results', 'import_gazepoint_pyhrv_results', 'run_gazepoint_pyhrv_style']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['prepare_gazepoint_heartpy_input', 'export_gazepoint_heartpy_input', 'reconstruct_gazepoint_ppg_clipping', 'enhance_gazepoint_ppg_peaks', 'filter_gazepoint_ppg_butterworth', 'correct_gazepoint_ppg_hampel', 'detect_gazepoint_ppg_peaks', 'reject_gazepoint_ppg_peaks', 'compute_gazepoint_ppg_measures', 'estimate_gazepoint_breathing_rate_from_ibi', 'plot_gazepoint_ppg_peak_detection', 'create_gazepoint_heartpy_report', 'run_gazepoint_heartpy_crosscheck', 'estimate_gazepoint_samplerate_mstimer', 'estimate_gazepoint_samplerate_datetime', 'scale_gazepoint_ppg_signal', 'scale_gazepoint_ppg_sections', 'flip_gazepoint_ppg_signal', 'remove_gazepoint_ppg_baseline_wander', 'smooth_gazepoint_ppg_signal', 'filter_gazepoint_ppg_signal', 'clean_gazepoint_rr_intervals', 'compute_gazepoint_ppg_frequency_measures', 'process_gazepoint_ppg_heartpy_style', 'process_gazepoint_ppg_segmentwise', 'plot_gazepoint_ppg_segmentwise', 'plot_gazepoint_ppg_poincare', 'plot_gazepoint_ppg_breathing', 'check_gazepoint_ppg_binary_quality']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['audit_gazepoint_ibi_quality', 'summarise_gazepoint_ibi_windows', 'classify_gazepoint_scr_intervals', 'flag_kleckner_eda_artifacts', 'convert_gazepoint_gsr_to_conductance', 'summarise_gazepoint_gsr_tonic_phasic']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['extract_gazepoint_hrv_nonlinear', 'extract_gazepoint_eda_complexity', 'extract_gazepoint_hrv_fragmentation', 'extract_gazepoint_hrv_asymmetry', 'extract_gazepoint_hrv_rqa', 'extract_gazepoint_hrv_geometric', 'extract_gazepoint_pdr_signals', 'calculate_gazepoint_rsa']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['standardise_gazepoint_plot_contract', 'check_gazepoint_plot_contract', 'get_gazepoint_plot_data', 'get_gazepoint_plot_settings', 'prepare_gazepoint_rhrv_input', 'standardize_gazepoint_plot_contracts', 'create_gazepoint_biometrics_checklist', 'create_gazepoint_biometrics_methods_text', 'standardize_gazepoint_biometrics_within_unit', 'standardise_gazepoint_biometrics_within_unit', 'export_gazepoint_rhrv_input', 'prepare_gazepoint_neurokit_eda_input', 'run_gazepoint_neurokit_eda_crosscheck', 'estimate_gazepoint_signal_lag', 'audit_gazepoint_biometric_sync_drift', 'prepare_gazepoint_pyppg_input', 'assess_gazepoint_hrp_waveform_quality', 'decompose_gazepoint_eda', 'detect_gazepoint_scr_events']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['plot_gazepoint_biometric_signals', 'plot_gazepoint_biometric_quality', 'plot_gazepoint_signal_activity', 'plot_gazepoint_time_resets', 'plot_gazepoint_biometric_report_dashboard', 'plot_gazepoint_eda_decomposition', 'plot_gazepoint_scr_events', 'plot_gazepoint_multimodal_timeline', 'plot_gazepoint_scr_specification_curve', 'create_gazepoint_biometrics_feature_inventory', 'format_gazepoint_biometrics_feature_inventory', 'summarise_gazepoint_biometrics_feature_inventory', 'summarise_gazepoint_full_biometric_windows', 'prepare_gazepoint_multimodal_model_data', 'prepare_gazepoint_biometrics_lme_data', 'summarise_gazepoint_dial_windows', 'join_gazepoint_biometrics_to_gp3tools', 'run_gazepoint_biometrics_real_data_readiness', 'run_gazepoint_biometrics_workflow', 'diagnose_gazepoint_biometrics_workflow', 'summarise_gazepoint_biometrics_workflow', 'create_gazepoint_biometrics_report_tables', 'write_gazepoint_biometrics_report_tables', 'export_gazepoint_biometrics_report_bundle', 'create_gazepoint_biometrics_report']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['standardise_gazepoint_adaptive_ema', 'standardize_gazepoint_adaptive_ema', 'audit_gazepoint_gsr_units', 'downsample_gazepoint_data', 'audit_gazepoint_biometric_sampling', 'summarise_gazepoint_hrv_features', 'summarise_gazepoint_ibi_hrv_windows', 'recommend_gazepoint_biometric_exclusions', 'baseline_correct_gazepoint_pupil', 'plot_gazepoint_saccade_main_sequence', 'simulate_gazepoint_eye_data', 'simulate_gazepoint_biometrics']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['audit_gazepoint_eda_artifacts', 'detect_gazepoint_scr_peaks', 'summarise_gazepoint_scr_event_windows', 'screen_gazepoint_eda_nonresponders', 'prepare_gazepoint_scr_hurdle_model_data', 'run_gazepoint_scr_threshold_sensitivity', 'extract_gazepoint_eda_spectral_power', 'denoise_gazepoint_eda_wavelet', 'extract_gazepoint_eda_tvsymp', 'plot_gazepoint_eda_gram', 'extract_gazepoint_hrv_fuzzy_csi', 'extract_gazepoint_hrv_rcmse', 'test_gazepoint_hrv_nonlinearity', 'extract_gazepoint_respiration_ceemdan', 'fuse_gazepoint_respiration_kalman', 'flag_gazepoint_mad_artifacts', 'audit_gazepoint_distributional_drift', 'detect_gazepoint_doubly_stochastic_changepoints', 'extract_gazepoint_scr_recovery_times']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['analyze_gazepoint_ac_susceptance', 'run_gazepoint_automated_statistics', 'analyze_gazepoint_cardiorespiratory_causality', 'compare_gazepoint_conditions_bootstrap', 'prepare_gazepoint_ctsi_input', 'optimize_gazepoint_cvxeda_tau', 'create_gazepoint_eda_analysis_pipeline', 'run_gazepoint_eda_analysis_pipeline', 'import_gazepoint_lsl_xdf', 'run_gazepoint_online_design_optimization', 'prepare_gazepoint_pspm_dcm_input', 'run_gazepoint_scr_multiverse']]))
IMPLEMENTED_EXPORTS = list(dict.fromkeys([*IMPLEMENTED_EXPORTS, *['assign_gazepoint_aoi', 'audit_gazepoint_smoke_privacy', 'check_gazepoint_bids', 'create_gazepoint_preregistration_template', 'create_gazepoint_trial_regressors', 'denoise_gazepoint_eda_autoencoder', 'denoise_gazepoint_ppg_autoencoder', 'detect_gazepoint_fixations', 'detect_gazepoint_saccades', 'export_gazepoint_to_bids', 'flag_gazepoint_artifacts_svm', 'model_gazepoint_eda_point_process', 'model_gazepoint_hr_point_process', 'pipeline_comparison_dashboard', 'prepare_gazepoint_artifact_svm_features', 'prepare_gazepoint_eyetrackingr_input', 'prepare_gazepoint_gazer_input', 'prepare_gazepoint_pupillometryr_input', 'preprocess_gazepoint_all', 'report_gazepoint_data_quality', 'run_gazepoint_real_data_smoke', 'run_gpbiometrics_shiny', 'run_gpbiometrics_shiny_annotator', 'write_gazepoint_real_data_smoke']]))
PENDING_EXPORTS = [name for name in R_EXPORTS if name not in IMPLEMENTED_EXPORTS]

def _placeholder(name):
    def f(*args, **kwargs):
        raise ParityNotImplementedError(f"{name} is registered from gpbiometrics 2.0.0 but is not implemented in this reconstructed tranche.")
    f.__name__ = name
    return f

for _name in PENDING_EXPORTS:
    globals()[_name] = _placeholder(_name)

__version__ = "0.1.0"
__all__ = [*R_EXPORTS, "R_EXPORTS", "IMPLEMENTED_EXPORTS", "PENDING_EXPORTS", "ParityNotImplementedError", "ReportText", "kiosk_demo_files", "kiosk_demo_overview", "kiosk_demo_path", "kiosk_demo_trial_design", "load_kiosk_demo"]

# Python-native convenience helpers; intentionally not members of the frozen R_EXPORTS contract.
from .demo import kiosk_demo_files, kiosk_demo_overview, kiosk_demo_path, kiosk_demo_trial_design, load_kiosk_demo
