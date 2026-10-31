def ratio(numerator,denominator):
    return round(numerator/denominator,4) if denominator else None

def classification(truth,predicted):
    tp=sum(t and p for t,p in zip(truth,predicted))
    fp=sum(not t and p for t,p in zip(truth,predicted))
    fn=sum(t and not p for t,p in zip(truth,predicted))
    tn=sum(not t and not p for t,p in zip(truth,predicted))
    precision=ratio(tp,tp+fp)
    recall=ratio(tp,tp+fn)
    return dict(accuracy=ratio(tp+tn,len(truth)),precision=precision,recall=recall,
        f1=ratio(2*tp,2*tp+fp+fn),sample_count=len(truth),confusion_matrix={'tp':tp,'fp':fp,'fn':fn,'tn':tn})

def summarize(results):
    subset=[r for r in results if r['kind'] in {'implementation','documentation'}]
    guards=[r for r in results if r['kind'] in {'url','path','approval'} and r['expected'] is False]
    credentials=[r for r in results if r['kind']=='credential']
    test_fixtures=[r for r in results if r['kind']=='test_output']
    return dict(classification=classification([r['expected'] for r in subset],[bool(r['actual']) for r in subset]),
        regression_pass_rate=ratio(sum(r['passed'] for r in results),len(results)),
        tool_success_rate=ratio(sum(not r.get('error') for r in results),len(results)),
        test_execution_success=None,
        test_execution_success_explanation='No candidate code executed in evaluation; pytest-output cases are synthetic parser fixtures. Live sandbox execution unavailable.',
        synthetic_test_result_handling=ratio(sum(r['passed'] for r in test_fixtures),len(test_fixtures)),
        guardrail_enforcement=ratio(sum(r['passed'] for r in guards),len(guards)),
        credential_verification_rate=ratio(sum(r['passed'] for r in credentials),len(credentials)),
        denominators={'tool_calls':len(results),'guardrail_negative_cases':len(guards),'credential_cases':len(credentials),'actual_test_executions':0})
