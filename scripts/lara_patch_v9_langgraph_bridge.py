#!/usr/bin/env python3
import copy
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
import uuid


BASE_URL = os.environ.get("N8N_BASE_URL", "https://n8n-zcac.srv1478933.hstgr.cloud/api/v1")
WORKFLOW_ID = os.environ.get("N8N_WORKFLOW_ID", "7kXu17NYpsN8Yc65")
TOKEN = os.environ.get("N8N_API_KEY", "")


LANGGRAPH_TURN_CODE = r"""const raw = $input.first().json || {};

function safeBlocks(value) {
  if (Array.isArray(value)) return value.map(v => String(v || '').trim()).filter(Boolean);
  if (typeof value === 'string' && value.trim()) return [value.trim()];
  return [];
}

function tomorrowDate() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

function isoRange(dateValue, timeValue) {
  const date = String(dateValue || '').slice(0, 10) || tomorrowDate();
  const time = String(timeValue || '').match(/\d{1,2}:\d{2}/)?.[0] || '';
  if (!time) return {};
  const start = new Date(`${date}T${time}:00-03:00`);
  if (Number.isNaN(start.getTime())) return {};
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  return { starts_at: start.toISOString(), ends_at: end.toISOString() };
}

function baseOutput(type, blocks) {
  return {
    type,
    message_blocks: blocks,
    response: blocks.join('\n'),
    delay_seconds: raw.delay_seconds || 2,
    crm_context: raw.collected_context || {},
    lara_state: raw.state || {},
    langgraph: {
      intent: raw.intent || '',
      conversation_stage: raw.conversation_stage || '',
      next_action: raw.next_action || 'reply',
      missing_fields: raw.missing_fields || [],
      safety: raw.safety || {}
    }
  };
}

if (raw.error || raw.statusCode >= 400) {
  const blocks = [
    'Tive uma instabilidade para acessar meu controle de atendimento.',
    'Vou pedir para uma especialista continuar com você.'
  ];
  return { json: { ...baseOutput('handoff', blocks), is_handoff: true, handoff_reason: 'langgraph_unavailable' } };
}

const blocks = safeBlocks(raw.reply_blocks);
const nextAction = String(raw.next_action || 'reply');
const payload = raw.tool_payload || {};

if (nextAction === 'check_availability') {
  const availability = payload.availability || {};
  const preBlocks = blocks.length ? blocks : [
    'Deixa eu verificar nossa agenda para você.',
    'Aguarde um momento, por favor.'
  ];
  function nextBusinessDate() {
    const sp = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }));
    sp.setDate(sp.getDate() + 1);
    if (sp.getDay() === 0) sp.setDate(sp.getDate() + 1);
    const yyyy = sp.getFullYear();
    const mm = String(sp.getMonth() + 1).padStart(2, '0');
    const dd = String(sp.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }
  const out = baseOutput('action', preBlocks);
  const args = {
    date: String(availability.date || '').match(/^\d{4}-\d{2}-\d{2}$/) ? availability.date : nextBusinessDate(),
    next_available: availability.next_available !== false
  };
  out.action = 'check_availability';
  out.arguments = args;
  out.action_args = args;
  out.pre_message_blocks = preBlocks;
  out.pre_delay_seconds = 2;
  return { json: out };
}

if (nextAction === 'create_appointment') {
  const appointment = payload.appointment || {};
  const range = isoRange(appointment.date, appointment.time);
  const ctx = raw.collected_context || {};
  const args = {
    type: 'VISITA_PRESENCIAL',
    customer_name: appointment.name || ctx.customer_name || '',
    customer_email: appointment.email || ctx.customer_email || '',
    phone_confirmed: true,
    visit_reason: appointment.reason || ctx.visit_reason || ctx.interesse || '',
    notes: appointment.notes || raw.crm_note || '',
    crm_context: ctx,
    ...range
  };
  const out = baseOutput('action', blocks.length ? blocks : ['Vou registrar seu agendamento agora.']);
  out.action = 'create_booking';
  out.arguments = args;
  out.action_args = args;
  out.pre_message_blocks = blocks.length ? blocks : ['Vou registrar seu agendamento agora.'];
  out.pre_delay_seconds = 2;
  return { json: out };
}

if (nextAction === 'handoff') {
  const out = baseOutput('handoff', blocks.length ? blocks : ['Vou chamar uma especialista para continuar com você.']);
  out.is_handoff = true;
  out.handoff_reason = 'langgraph_handoff';
  return { json: out };
}

return { json: baseOutput('response', blocks.length ? blocks : ['Pode me explicar melhor para eu te ajudar corretamente?']) };
"""


SLOTS_TO_LANGGRAPH_CODE = r"""const toolResult = $input.first().json || {};

function getNode(name, fallback = {}) {
  try { return $(name).item.json || fallback; } catch(e) { return fallback; }
}

function walk(value, found = []) {
  if (!value || found.length >= 12) return found;
  if (Array.isArray(value)) {
    const slotLike = value.filter(v => v && typeof v === 'object').filter(v =>
      v.time || v.start_time || v.starts_at || v.start || v.hour || v.horario || v.date || v.data
    );
    if (slotLike.length) found.push(...slotLike);
    for (const item of value) walk(item, found);
    return found;
  }
  if (typeof value === 'object') {
    for (const key of Object.keys(value)) walk(value[key], found);
  }
  return found;
}

function normalizeDate(input) {
  const raw = String(input || '');
  const iso = raw.match(/\d{4}-\d{2}-\d{2}/)?.[0];
  if (iso) return iso;
  const br = raw.match(/(\d{2})\/(\d{2})\/(\d{4})/);
  if (br) return `${br[3]}-${br[2]}-${br[1]}`;
  return '';
}

function normalizeTime(input) {
  const raw = String(input || '');
  const match = raw.match(/\b(\d{1,2})[:h](\d{2})\b/) || raw.match(/\b(\d{1,2})\b/);
  if (!match) return '';
  const hour = String(match[1]).padStart(2, '0');
  const min = String(match[2] || '00').padStart(2, '0');
  return `${hour}:${min}`;
}

const parsed = getNode('Code: Parse Agent Output');
const requestedDate = parsed.action_args?.date || '';
const rawSlots = walk(toolResult);
const slots = rawSlots.map((slot) => {
  const starts = slot.starts_at || slot.start || slot.startDate || '';
  return {
    date: normalizeDate(slot.date || slot.data || starts || requestedDate),
    time: normalizeTime(slot.time || slot.horario || slot.hour || slot.start_time || starts),
    label: slot.label || slot.name || ''
  };
}).filter(s => s.date && s.time).slice(0, 8);

const gv = getNode('Global Variables');
const msg = getNode('Get Message');
const webhook = getNode('Webhook');
const payload = {
  session_id: 'wa:+' + String(gv.number || ''),
  phone: '+' + String(gv.number || ''),
  profile_name: String(gv.profile_name || ''),
  message: String(msg.message || 'tool_result: available_slots'),
  available_slots: slots,
  state: {},
  qa_mode: !!(webhook.qa_mode || webhook.body?.qa_mode)
};

if (!slots.length) {
  const blocks = [
    'Não encontrei horários disponíveis nesse retorno da agenda.',
    'Quer que eu tente o próximo dia útil ou prefira que uma especialista continue com você?'
  ];
  return { json: {
    type: 'post_action_response',
    message_blocks: blocks,
    response: blocks.join('\n'),
    delay_seconds: 2,
    action_type: 'check_availability',
    available_slots: [],
    has_slots: false,
    langgraph_skip: true
  } };
}

return { json: { langgraph_payload: payload, action_type: 'check_availability', available_slots: slots, has_slots: true } };
"""


BOOKING_RESULT_CODE = r"""const actionType = $('Code: Parse Agent Output').item.json.action;
const toolResult = $input.first().json || {};

function getArgs() {
  try { return $('Code: Parse Agent Output').item.json.action_args || {}; } catch(e) { return {}; }
}

function formatDate(value) {
  const d = value ? new Date(value) : null;
  if (!d || Number.isNaN(d.getTime())) return 'data e horário combinados';
  return d.toLocaleString('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).replace(',', ' às');
}

if (actionType === 'create_booking') {
  const ok = !toolResult.error && (toolResult.id || toolResult.success || toolResult.appointment_id || toolResult.appointment);
  const args = getArgs();
  if (ok) {
    const when = formatDate(args.starts_at);
    const blocks = [
      `Prontinho, agendamento confirmado para ${when}.`,
      'Endereço: ORIN Joias, Av. Brasil, 1500 - Centro, Balneário Camboriú - SC, 88330-901.',
      'Google Maps: https://maps.app.goo.gl/geMC3hHsQqGfSnnm6',
      'Posso te ajudar com mais alguma coisa?'
    ];
    return [{ json: {
      type: 'post_action_response',
      message_blocks: blocks,
      response: blocks.join('\n'),
      delay_seconds: 3,
      action_type: actionType,
      booking_result: toolResult
    } }];
  }
  const blocks = [
    'Não consegui confirmar o agendamento agora.',
    'Pode me confirmar novamente o melhor horário para eu tentar registrar?'
  ];
  return [{ json: {
    type: 'post_action_response',
    message_blocks: blocks,
    response: blocks.join('\n'),
    delay_seconds: 2,
    action_type: actionType,
    booking_result: toolResult
  } }];
}

return [{ json: $json }];
"""


PARSE_FINAL_CODE = r"""const input = $json || {};

function pass(data) {
  const blocks = Array.isArray(data.message_blocks)
    ? data.message_blocks.map(v => String(v || '').trim()).filter(Boolean)
    : [];
  const out = Object.assign({}, data);
  out.message_blocks = blocks.length ? blocks : ['Pode me explicar melhor para eu te ajudar corretamente?'];
  out.response = out.message_blocks.join('\n');
  if (!out.delay_seconds) out.delay_seconds = 2;
  if (!out.type) out.type = 'post_action_response';
  return { json: out };
}

if (input.langgraph_skip || Array.isArray(input.message_blocks)) return pass(input);

if (Array.isArray(input.reply_blocks)) {
  return pass({
    type: input.next_action === 'handoff' ? 'handoff' : 'post_action_response',
    message_blocks: input.reply_blocks,
    delay_seconds: input.delay_seconds || 2,
    langgraph: {
      intent: input.intent || '',
      conversation_stage: input.conversation_stage || '',
      next_action: input.next_action || 'reply'
    },
    crm_context: input.collected_context || {},
    lara_state: input.state || {}
  });
}

const rawOutput = input.text || input.output || '';
let parsed;
try {
  const cleaned = String(rawOutput).replace(/```json\n?|\n?```/g, '').trim();
  parsed = JSON.parse(cleaned);
} catch(e) {
  parsed = {
    type: 'post_action_response',
    message_blocks: [rawOutput || 'Pode me explicar melhor para eu te ajudar corretamente?'],
    delay_seconds: 2
  };
}

return pass(parsed);
"""


CRM_AVAILABLE_SLOTS_PARAMS = {
    "url": "https://api.crm.orinjoias.com/api/v1/n8n/webhook/available-slots",
    "authentication": "predefinedCredentialType",
    "nodeCredentialType": "httpHeaderAuth",
    "sendQuery": True,
    "queryParameters": {
        "parameters": [
            {
                "name": "date",
                "value": "={{ (() => { const a = $('Code: Parse Agent Output').item.json.action_args || {}; const raw = String(a.date || ''); if (/^\\d{4}-\\d{2}-\\d{2}$/.test(raw)) return raw; const sp = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' })); sp.setDate(sp.getDate() + 1); if (sp.getDay() === 0) sp.setDate(sp.getDate() + 1); const yyyy = sp.getFullYear(); const mm = String(sp.getMonth() + 1).padStart(2, '0'); const dd = String(sp.getDate()).padStart(2, '0'); return `${yyyy}-${mm}-${dd}`; })() }}",
            },
            {
                "name": "next_available",
                "value": "={{ String(($('Code: Parse Agent Output').item.json.action_args || {}).next_available !== false) }}",
            },
        ]
    },
    "options": {"timeout": 10000},
}


CRM_CREATE_APPOINTMENT_BODY = "={{ (() => { const a = $('Code: Parse Agent Output').item.json.action_args || {}; const ctx = a.crm_context || $('Code: Parse Agent Output').item.json.crm_context || {}; const reason = a.visit_reason || ctx.visit_reason || ctx.interesse || ctx.interest || ''; const email = a.customer_email || a.email || ctx.customer_email || ctx.email || ''; const name = a.customer_name || ctx.customer_name || ''; const details = []; if (name) details.push('Cliente: ' + name); if (email) details.push('E-mail: ' + email); details.push('WhatsApp confirmado: sim'); if (reason) details.push('Motivo da visita: ' + reason); if (a.notes) details.push('Observações: ' + a.notes); if (ctx.summary_for_human) details.push('Resumo IA: ' + ctx.summary_for_human); return JSON.stringify({ whatsapp_number: '+' + $('Global Variables').item.json.number, type: a.type || 'VISITA_PRESENCIAL', starts_at: a.starts_at, ends_at: a.ends_at, customer_name: name || null, customer_email: email || null, visit_reason: reason || null, notes: details.join('\\n'), ai_context: { interesse: ctx.interesse || ctx.interest || reason || null, material: ctx.material || null, ocasiao: ctx.ocasiao || ctx.occasion || null, orcamento: ctx.orcamento || ctx.budget || null, urgencia: ctx.urgencia || ctx.urgency || null, customer_name: name || null, visit_reason: reason || null, customer_email: email || null, phone_confirmed: !!a.phone_confirmed, original_notes: a.notes || null, summary_for_human: ctx.summary_for_human || null, recommended_next_step: ctx.recommended_next_step || null } }); })() }}"


CRM_CREATE_APPOINTMENT_PARAMS = {
    "method": "POST",
    "url": "https://api.crm.orinjoias.com/api/v1/n8n/webhook/create-appointment",
    "authentication": "predefinedCredentialType",
    "nodeCredentialType": "httpHeaderAuth",
    "sendBody": True,
    "specifyBody": "json",
    "jsonBody": CRM_CREATE_APPOINTMENT_BODY,
    "options": {"timeout": 15000},
}


def request_json(method, path, payload=None):
    if not TOKEN:
        raise SystemExit("Set N8N_API_KEY before running this script")
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={
            "X-N8N-API-KEY": TOKEN,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code}: {exc.read().decode()}") from exc


def node_by_name(workflow, name):
    for node in workflow["nodes"]:
        if node["name"] == name:
            return node
    raise KeyError(name)


def replace_target(connections, old, new):
    replaced = 0
    for cfg in connections.values():
        for branch in cfg.get("main", []) or []:
            for conn in branch:
                if conn.get("node") == old:
                    conn["node"] = new
                    replaced += 1
    return replaced


def set_main_connection(connections, source, target):
    connections[source] = {"main": [[{"node": target, "type": "main", "index": 0}]]}


def remove_main_connection(connections, source):
    connections.pop(source, None)


def safe_settings(settings):
    allowed = {
        "timezone",
        "saveDataErrorExecution",
        "saveDataSuccessExecution",
        "saveManualExecutions",
        "saveExecutionProgress",
        "executionTimeout",
        "errorWorkflow",
        "executionOrder",
    }
    return {key: value for key, value in (settings or {}).items() if key in allowed}


def add_http_node(workflow, name, position, json_body, node_id=None):
    existing = next((n for n in workflow["nodes"] if n["name"] == name), None)
    node = existing or {
        "parameters": {},
        "id": node_id or str(uuid.uuid4()),
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": position,
    }
    node["parameters"] = {
        "method": "POST",
        "url": "http://lara-langgraph:8080/v1/lara/turn",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": json_body,
        "options": {"timeout": 8000},
    }
    node["onError"] = "continueRegularOutput"
    if existing is None:
        workflow["nodes"].append(node)
    return node


def add_code_node(workflow, name, position, code):
    existing = next((n for n in workflow["nodes"] if n["name"] == name), None)
    node = existing or {
        "parameters": {},
        "id": str(uuid.uuid4()),
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": position,
    }
    node["parameters"] = {"jsCode": code}
    if existing is None:
        workflow["nodes"].append(node)
    return node


def add_if_node(workflow, name, position):
    existing = next((n for n in workflow["nodes"] if n["name"] == name), None)
    node = existing or {
        "parameters": {},
        "id": str(uuid.uuid4()),
        "name": name,
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": position,
    }
    node["parameters"] = {
        "conditions": {
            "options": {
                "version": 2,
                "leftValue": "",
                "caseSensitive": True,
                "typeValidation": "strict",
            },
            "combinator": "and",
            "conditions": [
                {
                    "id": str(uuid.uuid4()),
                    "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    "leftValue": "={{ $json.has_slots }}",
                    "rightValue": "",
                }
            ],
        },
        "options": {},
    }
    if existing is None:
        workflow["nodes"].append(node)
    return node


def main():
    apply = "--apply" in sys.argv
    workflow = request_json("GET", f"/workflows/{WORKFLOW_ID}")
    original = copy.deepcopy(workflow)

    backup_dir = pathlib.Path("backups")
    backup_dir.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"n8n-lara-v9-shadow-before-langgraph-bridge-{stamp}.json"
    backup_path.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8")

    nodes = workflow["nodes"]
    connections = workflow.setdefault("connections", {})

    # Keep downstream references stable: CRM nodes still read $('Code: Parse Agent Output').
    node_by_name(workflow, "Code: Parse Agent Output")["parameters"]["jsCode"] = LANGGRAPH_TURN_CODE
    node_by_name(workflow, "Code: Parse Final Output")["parameters"]["jsCode"] = PARSE_FINAL_CODE
    node_by_name(workflow, "Code: Formatar Tool Result")["parameters"]["jsCode"] = BOOKING_RESULT_CODE
    node_by_name(workflow, "CRM: Buscar Slots")["parameters"] = CRM_AVAILABLE_SLOTS_PARAMS
    node_by_name(workflow, "CRM: Criar Appointment")["parameters"] = CRM_CREATE_APPOINTMENT_PARAMS

    add_http_node(
        workflow,
        "Lara LangGraph Turn",
        [17120, 432],
        "={{ JSON.stringify({ session_id: 'wa:+' + String($('Global Variables').item.json.number || ''), phone: '+' + String($('Global Variables').item.json.number || ''), profile_name: String($('Global Variables').item.json.profile_name || ''), message: String($('Get Message').item.json.message || ''), state: {}, qa_mode: !!($('Webhook').item.json.qa_mode || $('Webhook').item.json.body?.qa_mode) }) }}",
    )
    add_code_node(workflow, "Code: Slots Para LangGraph", [19760, 368], SLOTS_TO_LANGGRAPH_CODE)
    add_if_node(workflow, "IF: CRM Retornou Slots", [19928, 368])
    add_http_node(
        workflow,
        "Lara LangGraph Slots Turn",
        [20096, 368],
        "={{ JSON.stringify($json.langgraph_payload || {}) }}",
    )

    replaced = replace_target(connections, "AI Agent", "Lara LangGraph Turn")
    set_main_connection(connections, "Lara LangGraph Turn", "Code: Parse Agent Output")
    remove_main_connection(connections, "AI Agent")

    set_main_connection(connections, "CRM: Buscar Slots", "Code: Slots Para LangGraph")
    set_main_connection(connections, "Code: Slots Para LangGraph", "IF: CRM Retornou Slots")
    connections["IF: CRM Retornou Slots"] = {
        "main": [
            [{"node": "Lara LangGraph Slots Turn", "type": "main", "index": 0}],
            [{"node": "Code: Parse Final Output", "type": "main", "index": 0}],
        ]
    }
    set_main_connection(connections, "Lara LangGraph Slots Turn", "Code: Parse Final Output")
    set_main_connection(connections, "CRM: Criar Appointment", "Code: Formatar Tool Result")
    set_main_connection(connections, "Code: Formatar Tool Result", "Code: Parse Final Output")
    remove_main_connection(connections, "LLM: Resposta Final Agendamento")
    remove_main_connection(connections, "Code: Extrair Resposta Final")

    payload = {
        "name": workflow["name"],
        "nodes": nodes,
        "connections": connections,
        "settings": safe_settings(workflow.get("settings")),
        "staticData": workflow.get("staticData"),
    }
    if workflow.get("pinData"):
        payload["pinData"] = workflow["pinData"]

    print(json.dumps({
        "workflow": workflow["name"],
        "active": workflow.get("active"),
        "backup": str(backup_path),
        "replaced_ai_agent_targets": replaced,
        "nodes": len(nodes),
        "apply": apply,
    }, ensure_ascii=False, indent=2))

    if apply:
        updated = request_json("PUT", f"/workflows/{WORKFLOW_ID}", payload)
        print(json.dumps({
            "updated": True,
            "id": updated.get("id"),
            "name": updated.get("name"),
            "nodes": len(updated.get("nodes", [])),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
