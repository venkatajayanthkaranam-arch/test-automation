import re
import os
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment

CANONICAL_FIELDS = {
    'step_id': {
        'keywords': ['step id', 'test step id', 'step no', 'step number', 'seq', 's.no', 'step#', 'id'],
        'patterns': [r'^[a-zA-Z0-9_-]+\.\d+$', r'^\d+$', r'^[a-zA-Z]+[-_]\d+$', r'^step\s*\d+$'],
        'weight': 1.5,
    },
    'process_step': {
        'keywords': ['fusion process step', 'process step', 'process', 'flow step', 'section', 'group'],
        'patterns': [r'^[A-Z][a-zA-Z0-9\s]{3,30}$'],
        'weight': 0.9,
    },
    'role': {
        'keywords': ['role', 'user role', 'tester role', 'persona', 'run as', 'assigned role', 'user'],
        'patterns': [r'^(1st|2nd|3rd|first|second)?\s*(approver|recruiter|manager|employee|buyer|specialist|admin|tester)$', r'^[a-zA-Z\s]{3,25}$'],
        'weight': 1.2,
    },
    'description': {
        'keywords': ['test step description', 'step description', 'description', 'action', 'action / description', 'test action', 'instruction', 'steps'],
        'patterns': [r'^(click|login|navigate|enter|select|verify|open|choose|fill|scroll|switch|press)\b.*', r'.{15,}'],
        'weight': 1.6,
    },
    'test_data': {
        'keywords': ['test data', 'data', 'input', 'input data', 'values', 'parameters', 'test value'],
        'patterns': [r'^<blank>$', r'^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+$', r'^[\$\¥\€\£]?\s*\d+([\.,]\d+)?$', r'^n/a$', r'^[A-Za-z0-9_\-\s]{1,30}$'],
        'weight': 1.3,
    },
    'expected_result': {
        'keywords': ['expected results', 'expected result', 'expected', 'acceptance criteria', 'success condition', 'outcome'],
        'patterns': [r'^(should|verify|system displays|user is able|notification appears|success|approved|navigated|shown)\b.*', r'.{15,}'],
        'weight': 1.4,
    },
    'observed_result': {
        'keywords': ['observed results', 'observed result', 'actual result', 'actual', 'observed', 'comments / observed'],
        'patterns': [],
        'weight': 1.2,
    },
    'status': {
        'keywords': ['status', 'pass / fail status', 'test status', 'result', 'execution status', 'step status'],
        'patterns': [r'^(pass|fail|blocked|not attempted|in progress|manual required|not started|completed|skipped|p|f|n/a)$'],
        'weight': 1.5,
    },
    'sr_number': {
        'keywords': ['sr number/incident id(s)', 'sr number', 'incident id', 'bug id', 'jira id', 'defect id', 'ticket'],
        'patterns': [r'^(sr|bug|inc|jira|def)[-_\s]?\d+$'],
        'weight': 0.8,
    },
    'notes': {
        'keywords': ['notes (e.g. incident description)', 'notes', 'comments', 'remarks', 'incident description'],
        'patterns': [],
        'weight': 0.8,
    }
}

class ColumnMatcher:
    def __init__(self, cache_file: Optional[str] = None):
        if cache_file:
            self.cache_file = os.path.abspath(cache_file)
        else:
            self.cache_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'template_cache.json'))
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_to_cache(self, fingerprint: str, mapping: Dict[str, int]):
        self._cache[fingerprint] = mapping
        dir_name = os.path.dirname(self.cache_file)
        if dir_name and not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name, exist_ok=True)
            except Exception:
                pass
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            pass

    def compute_fingerprint(self, headers: List[str]) -> str:
        norm = [re.sub(r'[^a-z0-9]', '', str(h).lower()) for h in headers if h]
        return hashlib.sha256('|'.join(norm).encode('utf-8')).hexdigest()[:16]

    def score_column_header(self, header: str, field_def: Dict[str, Any]) -> float:
        if not header:
            return 0.0
        h_norm = re.sub(r'[^a-z0-9\s]', '', str(header).lower()).strip()
        
        for kw in field_def['keywords']:
            kw_norm = re.sub(r'[^a-z0-9\s]', '', kw.lower()).strip()
            if h_norm == kw_norm:
                return 1.0
            if kw_norm in h_norm or h_norm in kw_norm:
                return 0.75
        
        h_tokens = set(h_norm.split())
        best_token_score = 0.0
        for kw in field_def['keywords']:
            kw_tokens = set(kw.lower().split())
            if not kw_tokens:
                continue
            inter = len(h_tokens.intersection(kw_tokens))
            score = inter / len(kw_tokens)
            if score > best_token_score:
                best_token_score = score
                
        return best_token_score * 0.65

    def score_column_samples(self, samples: List[Any], field_def: Dict[str, Any]) -> float:
        if not samples or not field_def.get('patterns'):
            return 0.0
        
        valid_samples = [str(s).strip() for s in samples if s is not None and str(s).strip()]
        if not valid_samples:
            return 0.0
            
        matches = 0
        for val in valid_samples:
            for pattern in field_def['patterns']:
                if re.search(pattern, val, re.IGNORECASE):
                    matches += 1
                    break
                    
        return min(1.0, matches / len(valid_samples))

    def match_columns(self, headers: List[str], sample_rows: List[List[Any]]) -> Tuple[Dict[str, int], float]:
        fingerprint = self.compute_fingerprint(headers)
        if fingerprint in self._cache:
            cached_map = self._cache[fingerprint]
            return cached_map, 1.0

        n_cols = len(headers)
        canonical_keys = list(CANONICAL_FIELDS.keys())
        n_fields = len(canonical_keys)

        col_samples = [[] for _ in range(n_cols)]
        for row in sample_rows:
            for c_idx in range(min(n_cols, len(row))):
                col_samples[c_idx].append(row[c_idx])

        score_matrix = np.zeros((n_fields, n_cols))
        
        for f_idx, field_key in enumerate(canonical_keys):
            f_def = CANONICAL_FIELDS[field_key]
            for c_idx in range(n_cols):
                h_text = headers[c_idx] if c_idx < len(headers) else ''
                h_score = self.score_column_header(h_text, f_def)
                s_score = self.score_column_samples(col_samples[c_idx], f_def)
                
                combined = (h_score * 0.7) + (s_score * 0.3)
                if h_score > 0.6 and s_score > 0.4:
                    combined = min(1.0, combined + 0.2)
                score_matrix[f_idx, c_idx] = combined * f_def['weight']

        cost_matrix = -score_matrix
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        mapping: Dict[str, int] = {}
        total_assigned_score = 0.0
        assigned_count = 0

        for r, c in zip(row_ind, col_ind):
            field_name = canonical_keys[r]
            assigned_score = score_matrix[r, c] / CANONICAL_FIELDS[field_name]['weight']
            if assigned_score >= 0.25 or (field_name in ['status', 'observed_result', 'notes', 'sr_number'] and assigned_score >= 0.15):
                mapping[field_name] = int(c)
                total_assigned_score += assigned_score
                assigned_count += 1

        overall_confidence = (total_assigned_score / max(1, assigned_count)) if assigned_count else 0.0
        
        if overall_confidence >= 0.70:
            self.save_to_cache(fingerprint, mapping)

        return mapping, round(overall_confidence, 3)
