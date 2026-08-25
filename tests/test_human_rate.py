import json
from pathlib import Path
from bin.human_rate import load_ledger, save_human_ratings, _print_comparison

def test_load_ledger(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    with open(ledger_path, "w") as f:
        f.write('{"iteration": 1, "verdict": {"facial_similarity": 8.0, "adherence_score": 7.5}}\n')
        f.write('{"iteration": 2, "verdict": {"facial_similarity": 5.0, "adherence_score": 6.0}}\n')
    
    records = load_ledger(ledger_path)
    assert len(records) == 2
    assert records[0]["iteration"] == 1
    assert records[1]["verdict"]["adherence_score"] == 6.0

def test_save_human_ratings(tmp_path):
    records = [
        {"iteration": 1, "human_eval": {"facial_similarity": 9.0, "status": "RATED"}},
        {"iteration": 2, "human_eval": {"status": "PENDING_HUMAN"}},
    ]
    output_path = tmp_path / "out.jsonl"
    save_human_ratings(records, output_path)
    
    assert output_path.exists()
    lines = output_path.read_text().strip().split('\n')
    assert len(lines) == 2
    data1 = json.loads(lines[0])
    assert data1["iteration"] == 1
    assert data1["human_eval"]["facial_similarity"] == 9.0

def test_round_trip(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    with open(ledger_path, "w") as f:
        f.write('{"iteration": 1, "verdict": {"facial_similarity": 8.0}}\n')
    
    records = load_ledger(ledger_path)
    records[0]["human_eval"] = {"facial_similarity": 7.0, "status": "RATED"}
    
    out_path = tmp_path / "out.jsonl"
    save_human_ratings(records, out_path)
    
    reloaded = load_ledger(out_path)
    assert len(reloaded) == 1
    assert reloaded[0]["verdict"]["facial_similarity"] == 8.0
    assert reloaded[0]["human_eval"]["facial_similarity"] == 7.0

def test_print_comparison_no_crash(capsys):
    records = [
        {
            "iteration": 1,
            "verdict": {"facial_similarity": 8.0, "adherence_score": 7.5},
            "human_eval": {"facial_similarity": 9.0, "adherence_score": 7.0, "status": "RATED"}
        },
        {
            "iteration": 2,
            "verdict": {"facial_similarity": 5.0, "adherence_score": 6.0},
            "human_eval": {"status": "PENDING_HUMAN"}
        }
    ]
    _print_comparison(records)
    captured = capsys.readouterr()
    assert "vs" in captured.out
    assert "8.0" in captured.out
    assert "9.0" in captured.out

def test_print_comparison_empty(capsys):
    _print_comparison([])
    captured = capsys.readouterr()
    assert "vs" in captured.out
