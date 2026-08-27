from __future__ import annotations
import contextlib, io, json, runpy, subprocess, sys
from pathlib import Path
import gpbiometricspy as gp

ROOT=Path(__file__).resolve().parents[1]

def test_development_version_and_stable_contract():
    assert gp.__version__=='0.1.1.dev0'; assert len(gp.R_EXPORTS)==406; assert len(gp.IMPLEMENTED_EXPORTS)==406; assert len(gp.PENDING_EXPORTS)==0

def test_golden_manifest_and_python_generation(tmp_path):
    manifest=json.loads((ROOT/'reference/golden/manifest.json').read_text()); assert len(manifest['cases'])>=15
    out=tmp_path/'python.json'; subprocess.run([sys.executable,str(ROOT/'scripts/generate_python_golden.py'),'--output',str(out)],cwd=ROOT,check=True)
    data=json.loads(out.read_text()); assert set(data)=={c['id'] for c in manifest['cases']}

def test_r_golden_writer_preserves_full_precision():
    text=(ROOT/'reference/golden/generate_r_golden.R').read_text()
    assert 'digits=NA' in text.replace(' ', '')

def test_all_26_executable_tutorials():
    scripts=sorted(p for p in (ROOT/'examples/tutorials').glob('*.py') if p.name!='_shared.py'); assert len(scripts)==26
    tutorial_dir=str(ROOT/'examples/tutorials')
    if tutorial_dir not in sys.path: sys.path.insert(0,tutorial_dir)
    for script in scripts:
        buf=io.StringIO()
        with contextlib.redirect_stdout(buf):
            runpy.run_path(str(script),run_name=f"__tutorial_{script.stem.replace('-', '_')}__")
        assert '"status": "PASS"' in buf.getvalue(), f'{script.name} did not report PASS: {buf.getvalue()}'

def test_repository_security_and_validation_files_exist():
    expected=['.github/dependabot.yml','.github/workflows/codeql.yml','.github/workflows/deep-parity.yml','.github/workflows/interoperability.yml','.github/workflows/real-data-validation.yml','.github/ISSUE_TEMPLATE/bug_report.yml','.github/ISSUE_TEMPLATE/feature_request.yml','scripts/validate_real_data.py']
    for rel in expected: assert (ROOT/rel).exists(), rel

def test_real_data_validator_runs_outside_repository(tmp_path):
    data_dir=tmp_path/'private_input'; data_dir.mkdir()
    output_dir=tmp_path/'private_output'
    gp.load_kiosk_demo(participants=['synthetic_kiosk_p001']).iloc[:600].to_csv(data_dir/'profile.csv',index=False)
    cp=subprocess.run([sys.executable,str(ROOT/'scripts/validate_real_data.py'),str(data_dir/'profile.csv'),'--output',str(output_dir)],cwd=ROOT,text=True,capture_output=True,timeout=45)
    assert cp.returncode==0, f'STDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}'
    summary=json.loads((output_dir/'gpbiometricspy_real_data_validation_summary.json').read_text())
    assert summary['mode']=='single_file'
    assert summary['rows']==600
    for required in ['import_schema_audit','active_channels','real_data_readiness','eda_quality','ppg_peak_detection','hrv_features','pupil_cleaning','gaze_validation','ttl_event_extraction','aggregate_report_bundle']:
        assert required in summary['steps'], required


def test_optional_backend_compatibility_dependencies_are_declared():
    pyproject=(ROOT/'pyproject.toml').read_text().lower()
    workflow=(ROOT/'.github/workflows/interoperability.yml').read_text().lower()
    assert 'peakutils>=1.3.4' in pyproject
    assert 'setuptools>=77,<82' in pyproject
    assert 'peakutils>=1.3.4' in workflow
    assert 'setuptools>=77,<82' in workflow
