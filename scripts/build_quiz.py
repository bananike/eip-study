#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily/*.md → quiz.json 파서. 섹션 기반으로 문제/정답/해설 추출."""
import os, re, json, glob

OPT_MARKS = ['①','②','③','④']
OPT_IDX = {m:i for i,m in enumerate(OPT_MARKS)}

def split_sections(text):
    """## 헤더 기준으로 (title, body) 리스트 반환. 첫 # 제목은 별도."""
    lines = text.split('\n')
    title = lines[0].lstrip('# ').strip() if lines and lines[0].startswith('# ') else ''
    secs = []
    cur_title, cur_body = None, []
    for ln in lines[1:]:
        m = re.match(r'^##\s+(.*)$', ln)
        if m:
            if cur_title is not None:
                secs.append((cur_title, '\n'.join(cur_body).strip()))
            cur_title = m.group(1).strip()
            cur_body = []
        else:
            if cur_title is not None:
                cur_body.append(ln)
    if cur_title is not None:
        secs.append((cur_title, '\n'.join(cur_body).strip()))
    return title, secs

def find_section(secs, *keywords):
    for t, b in secs:
        if any(k in t for k in keywords):
            return b
    return ''

def parse_questions(body):
    """기출 섹션 body → [{n, source, stem_md, options[4]}]"""
    qs = []
    # ### 문제 N [source] 로 분할
    parts = re.split(r'^###\s+문제\s+(\d+)\s*(\[[^\]]*\])?\s*$', body, flags=re.M)
    # parts: [pre, n1, src1, body1, n2, src2, body2, ...]
    i = 1
    while i < len(parts):
        n = int(parts[i])
        src = (parts[i+1] or '').strip('[]') if parts[i+1] else ''
        qbody = parts[i+2]
        i += 3
        # qbody에서 --- 이후 잘라내기 (구분선)
        qbody = re.split(r'^---\s*$', qbody, flags=re.M)[0]
        # 옵션 라인 추출
        opt_lines = {}
        stem_lines = []
        in_code = False
        for ln in qbody.split('\n'):
            if ln.strip().startswith('```'):
                in_code = not in_code
                stem_lines.append(ln); continue
            m = re.match(r'^\s*([①②③④])\s*(.*)$', ln)
            if m and not in_code:
                opt_lines[OPT_IDX[m.group(1)]] = m.group(2).strip()
            else:
                if not opt_lines:  # 옵션 시작 전까지만 stem
                    stem_lines.append(ln)
        stem = '\n'.join(stem_lines).strip()
        options = [opt_lines.get(k,'') for k in range(4)]
        if sum(1 for o in options if o) >= 2:  # 최소 2개 옵션 있어야 유효
            qs.append({'n':n,'source':src,'stem_md':stem,'options':options})
    return qs

def parse_answers(body):
    """정답표 body → {n: ans_idx}"""
    ans = {}
    for ln in body.split('\n'):
        m = re.match(r'^\|\s*(\d+)\s*\|\s*([①②③④])\s*\|', ln)
        if m:
            ans[int(m.group(1))] = OPT_IDX[m.group(2)]
    return ans

def parse_explanations(body):
    """해설 body → {n: md}"""
    ex = {}
    parts = re.split(r'^###\s+문제\s+(\d+)\s*$', body, flags=re.M)
    i = 1
    while i < len(parts):
        n = int(parts[i]); content = parts[i+1]
        content = re.split(r'^---\s*$', content, flags=re.M)[0]
        ex[n] = content.strip()
        i += 2
    return ex

def parse_file(path):
    text = open(path, encoding='utf-8').read()
    title, secs = split_sections(text)
    # title 예: "Day 7 · [4과목 ...] Java 객체지향 ..."
    mday = re.search(r'Day\s+(\d+)', title)
    day = int(mday.group(1)) if mday else 0
    msub = re.search(r'\[([^\]]+)\]', title)
    subject = msub.group(1).strip() if msub else ''
    topic = title.split(']')[-1].strip() if ']' in title else title
    date = os.path.basename(path).replace('.md','')

    qbody = find_section(secs, '오늘의 기출', '기출 8문제', '기출문제')
    abody = find_section(secs, '정답표')
    ebody = find_section(secs, '상세 해설', '해설')

    qs = parse_questions(qbody)
    ans = parse_answers(abody)
    ex = parse_explanations(ebody)
    for q in qs:
        q['answer'] = ans.get(q['n'], None)
        q['explanation_md'] = ex.get(q['n'], '')
    return {'day':day,'date':date,'subject':subject,'topic':topic,'questions':qs}

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = sorted(glob.glob(os.path.join(root,'daily','2026-*.md')))
    days = [parse_file(f) for f in files]
    days = [d for d in days if d['questions']]
    days.sort(key=lambda d:d['day'])
    out = {'generated':'auto','days':days}
    outpath = os.path.join(root,'quiz.json')
    json.dump(out, open(outpath,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    # 검증 리포트
    total_q = sum(len(d['questions']) for d in days)
    no_ans = sum(1 for d in days for q in d['questions'] if q['answer'] is None)
    print(f"파일 {len(days)}개 / 총 문제 {total_q}개 / 정답누락 {no_ans}개")
    for d in days:
        miss = [q['n'] for q in d['questions'] if q['answer'] is None]
        flag = f" ⚠누락:{miss}" if miss else ""
        print(f"  Day {d['day']} ({d['date']}): {len(d['questions'])}문제{flag}")

if __name__=='__main__':
    main()
