"""R20 report tests."""
import csv
import pytest
from kimarite.r20_gauntlet_report import report, wilson

def test_wilson_bounds():
    assert wilson(0, 0) == (None, None)
    low, high = wilson(5, 10)
    assert 0 <= low < 0.5 < high <= 1

def test_duplicate_batch_fixtures_fail(tmp_path):
    fields = ["arm_id","kimarite","placement","fixture_id","seed","subject_index","opponent_index","subject_seat","subject_won","completed","finished_by_tested_kimarite","condition_attained","tested_card_available","win_method","turns","error"]
    line = ["HIK-3","Hikiotoshi","starting","001-01",1234,1,11,"A",True,True,False,False,True,"Yorikiri",2,""]
    path = tmp_path/"dup.csv"
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.writer(handle)
        writer.writerow(fields)
        writer.writerow(line)
        writer.writerow(line)
    with pytest.raises(ValueError,match="Duplicate"):
        report([path])
