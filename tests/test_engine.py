from thai_legal_mcp.research_engine import decompose_issues, evidence_grade, hash_text

def test_issue_decomposition_detects_core_issues():
    issues = decompose_issues('พ่อใช้มีดฟันลูกจนบาดเจ็บ ลูกต้องการฟ้อง')
    labels = {x['issue'] for x in issues}
    assert 'องค์ประกอบความผิด/การกระทำ' in labels
    assert 'ความสัมพันธ์ของคู่กรณี' in labels
    assert 'อำนาจฟ้อง/สิทธิผู้เสียหาย' in labels

def test_evidence_grade():
    assert evidence_grade('ocs', True) == 'A'
    assert evidence_grade('ocs', False) == 'B'
    assert evidence_grade('unknown', False) == 'X'

def test_hash_is_stable():
    assert hash_text('กฎหมาย') == hash_text('กฎหมาย')
