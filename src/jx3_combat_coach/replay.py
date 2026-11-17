"""Replay actual observations; never derive damage from health deltas."""
from jx3_combat_coach.models import Analysis
from jx3_combat_coach.knowledge.catalog import ReferenceCatalog


def fields(table):
    return {k: v for k, v in table.get('$table', []) if type(k) is int} if isinstance(table, dict) else {}


def number(value):
    return value if type(value) in (int, float) else None


def replay(analysis: Analysis):
    catalog = ReferenceCatalog()
    events, players, health = [], {}, {}
    start = analysis.parsed.events[0].client_ms if analysis.parsed.events else 0
    previous = start
    warnings = ['资料版本与日志版本尚未匹配；控制、解控仅为参考标签，Buff 消失不代表成功解控。']
    for raw in analysis.parsed.events:
        p = fields(raw.payload)
        actor = target = resource_id = level = None
        kind, values = 'unknown', {}
        if raw.client_ms < previous:
            warnings.append(f'第 {raw.line_number} 行客户端时钟倒退；回放保留文件顺序。')
        previous = raw.client_ms
        if raw.event_code == 4:
            actor, kind = p.get(1), 'player'
            if type(actor) is int:
                info = players.setdefault(str(actor), {'id': str(actor)})
                for key, idx in [('name', 2), ('force_id', 3), ('kungfu_id', 4)]:
                    if idx in p: info[key] = p[idx]
                values = dict(info)
        elif raw.event_code == 5:
            target, kind = p.get(1), 'health'
            values = {k: p[i] for k, i in [('health', 3), ('max_health', 4)] if number(p.get(i)) is not None and p[i] >= 0}
        elif raw.event_code == 29:
            target, kind = p.get(2), 'snapshot'
            values = {k: p[i] for k, i in [('x', 3), ('y', 4), ('z', 5), ('health', 7), ('max_health', 8)] if number(p.get(i)) is not None and (i in (3, 4, 5) or p[i] >= 0)}
            values['target_type_raw'] = p.get(1)
        elif raw.event_code in (19, 20):
            actor, resource_id, level = p.get(1), p.get(2), p.get(3)
            kind = 'cast' if raw.event_code == 19 else 'cast_response'
            values = {'response_raw': p.get(4)} if raw.event_code == 20 else {}
        elif raw.event_code == 13:
            target, actor, resource_id, level = p.get(1), p.get(10), p.get(5), p.get(9)
            kind = 'buff_remove' if p.get(2) in (True, 1) else 'buff_update'
            values = {'index': p.get(3), 'stack': p.get(6), 'end_frame': p.get(7), 'delete_raw': p.get(2)}
        elif raw.event_code == 21:
            actor, target, resource_id, level, kind = p.get(1), p.get(2), p.get(5), p.get(6), 'effect'
            results = fields(p.get(9))
            values = {'scheme_raw': p.get(4), 'critical_raw': p.get(7), 'results': results}
            for key, idx in [('effective_damage', 13), ('effective_heal', 14)]:
                if number(results.get(idx)) is not None: values[key] = results[idx]
        elif raw.event_code == 27:
            target, kind, values = p.get(1), 'health_delta', {'delta': p.get(2)}
        elif raw.event_code == 28:
            target, actor, kind = p.get(1), p.get(2), 'death'
        reference = None
        if resource_id is not None:
            resource_kind = 'buff' if raw.event_code == 13 else ('skill' if raw.event_code in (19, 20) or p.get(4) == 1 else None)
            if resource_kind: reference = catalog.lookup(resource_kind, str(resource_id), level)
        events.append(dict(event_id=raw.event_id, sequence=raw.line_number, time_ms=raw.client_ms-start,
                           timestamp_ms=raw.client_ms, kind=kind, actor_id=str(actor) if type(actor) is int else None,
                           target_id=str(target) if type(target) is int else None, resource_id=resource_id,
                           level=level, reference=reference, values=values))
    return dict(events=events, players=list(players.values()), warnings=list(dict.fromkeys(warnings)),
                catalog_entries=len(catalog.data['entries']), catalog_version=catalog.data.get('game_version'))


def evidence_report(view):
    sections = []
    events = view['events']
    for index, death in enumerate(events):
        if death['kind'] != 'death': continue
        window = [e for e in events[:index+1] if death['timestamp_ms']-10000 <= e['timestamp_ms'] <= death['timestamp_ms'] and (e['target_id'] == death['target_id'] or e['actor_id'] == death['target_id'])]
        damage = sum(e['values'].get('effective_damage', 0) for e in window if e['target_id'] == death['target_id'])
        heal = sum(e['values'].get('effective_heal', 0) for e in window if e['target_id'] == death['target_id'])
        sections.append(dict(target_id=death['target_id'], time_ms=death['time_ms'], summary=f'死亡前10秒，日志记录有效伤害 {damage}、有效治疗 {heal}；不据此断定唯一死因。', evidence_event_ids=[e['event_id'] for e in window]))
    return dict(mode='evidence', title='本地证据报告（非 AI）', deaths=sections, warnings=view['warnings'])
