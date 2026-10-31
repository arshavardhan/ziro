from evaluation.metrics import classification

def test_metrics_count_errors():
    result=classification([True,True,False,False],[True,False,True,False])
    assert result['accuracy']==.5
    assert result['precision']==.5
    assert result['recall']==.5
    assert result['f1']==.5
