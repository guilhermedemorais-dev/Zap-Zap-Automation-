#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import time
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("N8N_BASE_URL", "https://n8n-zcac.srv1478933.hstgr.cloud").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")
SHADOW_WORKFLOW_ID = os.environ.get("LARA_SHADOW_WORKFLOW_ID", "7kXu17NYpsN8Yc65")
SHADOW_WEBHOOK_PATH = os.environ.get("LARA_SHADOW_WEBHOOK_PATH", "whatsapp-inbound-v9-shadow")


ROOT_PARSER_JS = r"""
const raw     = ($('Get Message').item.json.message || '').trim();
const lower   = raw.toLowerCase().trim();
const session = $input.first().json.propertyName === '1';
const qaMode  = !!($('Filter UAZAPI').item.json.qa_mode || $('Filter UAZAPI').item.json.body?.qa_mode || $('Filter UAZAPI').item.json.body?.data?.qa_mode || $('Filter UAZAPI').item.json.data?.qa_mode || $('Webhook').item.json.body?.qa_mode || $('Webhook').item.json.qa_mode);

if (lower === 'root' || lower === '/root') {
  return [{ json: { command: 'welcome', args: '', raw, session_active: session } }];
}

function parseCmd(str) {
  const s = str.trim();
  const sl = s.toLowerCase();
  const sp = sl.indexOf(' ');
  const cmd  = sp === -1 ? sl : sl.slice(0, sp);
  const args = sp === -1 ? '' : s.slice(sp + 1).trim();
  return { cmd, args };
}

let cmdStr = null;
const isSlash = raw.startsWith('/');
if (lower.startsWith('/root '))              cmdStr = raw.slice(6);
else if (isSlash && (session || qaMode))      cmdStr = raw.slice(1);
else if (lower.startsWith('root '))          cmdStr = raw.slice(5);

if (session && raw === 'CONFIRMAR RESET') {
  return [{ json: { command:'confirm_reset', args:'', raw, session_active:true } }];
}

if (cmdStr !== null) {
  const { cmd, args } = parseCmd(cmdStr);
  const MAP = {
    'menu':'menu','status':'status','help':'help','tutorial':'tutorial','prompt':'prompt','system':'prompt',
    'log':'log','logs':'log','auditoria':'log','historico':'log','histórico':'log',
    'blocks':'blocks','blocos':'blocks','block':'block','bloco':'block','setblock':'setblock','setbloco':'setblock',
    'exit':'exit','rclear':'rclear','reset':'reset',
    'assumir':'assumir','devolver':'devolver','bot':'devolver',
    'regra':'regra','corrigir':'corrigir','persona':'persona',
    'objetivo':'objetivo','tom':'tom','exemplo':'exemplo',
    'escrita':'escrita','parametro':'parametro','parâmetro':'parametro',
    'newprompt':'newprompt','newparametro':'newprompt','newparamentro':'newprompt',
    'novoparametro':'newprompt','novoparamentro':'newprompt',
    'link':'link','links':'parametro',
    'buscar':'buscar','pesquisar':'buscar'
  };
  if (MAP[cmd]) {
    return [{ json: { command: MAP[cmd], args, raw, session_active: session } }];
  }
  return [{ json: { command:'unknown', args:raw, raw, session_active: session, unknown_command: cmd } }];
}

if (session) {
  const confirmWords = ['sim','s','yes','confirmar','confirma','ok','salvar','pode'];
  const cancelWords  = ['não','nao','n','no','cancelar','cancela','desistir'];
  if (confirmWords.includes(lower)) return [{ json: { command:'confirmar', args:'', raw, session_active:true } }];
  if (cancelWords.includes(lower))  return [{ json: { command:'cancelar',  args:'', raw, session_active:true } }];
  return [{ json: { command:'modo_livre', args:raw, raw, session_active:true } }];
}

return [{ json: { command:'ignore', args:'', raw, session_active:false } }];
""".strip() + "\n"


def request_json(path: str, *, method: str = "GET", data: dict | None = None, timeout: int = 120) -> dict:
    if not API_KEY:
        raise SystemExit("N8N_API_KEY is required.")

    headers = {"Accept": "application/json", "X-N8N-API-KEY": API_KEY}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, method=method, headers=headers)
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")
        raise RuntimeError(f"n8n HTTP {err.code}: {detail}") from err
    return json.loads(raw) if raw else {}


def node_by_name(workflow: dict, name: str) -> dict:
    for node in workflow.get("nodes") or []:
        if node.get("name") == name:
            return node
    raise KeyError(f"Node not found: {name}")


def patch_processar_comando(js: str) -> str:
    unknown_old = """} else if (command === 'unknown') {
  responseText = 'Comando não reconhecido.\\nUse /help para ver os comandos disponíveis.';
"""
    unknown_new = """} else if (command === 'unknown') {
  responseText = 'Comando não reconhecido.\\nVocê quis dizer /reset?\\nUse /help para ver os comandos disponíveis.';
"""
    if unknown_old in js:
        js = js.replace(unknown_old, unknown_new)

    reset_old = """} else if (command === 'reset') {
  config.rules=[]; config.corrections=[]; config.examples=[];
  config.objetivos=[]; config.persona_extra=''; config.tom=7;
  config.updated_at = new Date().toISOString();
  addAudit('reset', 'Configuração ROOT resetada');
  save = true;
  responseText = '🔄 Configurações resetadas.';
"""
    reset_new = """} else if (command === 'unknown') {
  responseText = 'Comando não reconhecido.\\nVocê quis dizer /reset?\\nUse /help para ver os comandos disponíveis.';

} else if (command === 'reset') {
  config._pending_reset = true;
  save = true;
  responseText = 'Atenção: /reset apaga toda a configuração atual da Lara.\\nPara confirmar, responda exatamente: CONFIRMAR RESET\\nPara cancelar, responda: cancelar';

} else if (command === 'confirm_reset') {
  if (config._pending_reset) {
    config.rules=[]; config.corrections=[]; config.examples=[];
    config.objetivos=[]; config.persona_extra=''; config.tom=7;
    delete config._pending;
    delete config._pending_reset;
    config.updated_at = new Date().toISOString();
    addAudit('reset', 'Configuração ROOT resetada com confirmação forte');
    save = true;
    responseText = 'Reset confirmado. A configuração da Lara foi restaurada para a base padrão.';
  } else {
    responseText = 'Não existe reset pendente.';
  }
"""
    if reset_old not in js:
        if "_pending_reset" not in js or "confirm_reset" not in js:
            raise RuntimeError("Reset branch not found in ROOT: Processar Comando")
    else:
        js = js.replace(reset_old, reset_new)

    cancelar_old = """} else if (command === 'cancelar') {
  if (config._pending) { delete config._pending; save=true; responseText='↩️ Cancelado.'; }
  else { responseText='ℹ️ Nada pendente.'; }
"""
    cancelar_new = """} else if (command === 'cancelar') {
  if (config._pending_reset) {
    delete config._pending_reset;
    save = true;
    responseText = 'Reset cancelado. Nenhuma configuração foi alterada.';
  } else if (config._pending) { delete config._pending; save=true; responseText='↩️ Cancelado.'; }
  else { responseText='ℹ️ Nada pendente.'; }
"""
    if cancelar_old not in js:
        if "_pending_reset" not in js:
            raise RuntimeError("Cancel branch not found in ROOT: Processar Comando")
    else:
        js = js.replace(cancelar_old, cancelar_new)

    keys_old = "'seguranca','root_blocks','audit_log','_pending'];"
    keys_new = "'seguranca','root_blocks','audit_log','_pending','_pending_reset','human_takeover_numbers'];"
    if keys_old not in js:
        if "_pending_reset" not in js and "human_takeover_numbers" not in js:
            raise RuntimeError("Config serialization keys not found")
    else:
        js = js.replace(keys_old, keys_new)

    assumir_marker = "} else if (['regra','corrigir','persona','objetivo','tom','exemplo','escrita','newprompt','link','setblock'].includes(command)) {"
    assumir_branch = """} else if (command === 'assumir') {
  const target = String(args || '').replace(/\\D+/g, '');
  config.human_takeover_numbers = Array.isArray(config.human_takeover_numbers) ? config.human_takeover_numbers : [];
  if (!target) {
    responseText = 'Informe o número do cliente. Ex: /assumir 554796963593';
  } else {
    const normalized = target.startsWith('55') ? target : '55' + target;
    if (!config.human_takeover_numbers.includes(normalized)) config.human_takeover_numbers.push(normalized);
    config.updated_at = new Date().toISOString();
    addAudit('assumir', normalized);
    save = true;
    responseText = 'Atendimento assumido. A Lara está pausada para este cliente.';
  }

} else if (command === 'devolver') {
  const target = String(args || '').replace(/\\D+/g, '');
  config.human_takeover_numbers = Array.isArray(config.human_takeover_numbers) ? config.human_takeover_numbers : [];
  if (!target) {
    responseText = 'Informe o número do cliente. Ex: /devolver 554796963593';
  } else {
    const normalized = target.startsWith('55') ? target : '55' + target;
    config.human_takeover_numbers = config.human_takeover_numbers.filter(x => x !== normalized);
    config.updated_at = new Date().toISOString();
    addAudit('devolver', normalized);
    save = true;
    responseText = 'Atendimento devolvido para a Lara.';
  }

"""
    if assumir_marker not in js:
        if "command === 'assumir'" not in js or "command === 'devolver'" not in js:
            raise RuntimeError("Config command branch not found")
    else:
        js = js.replace(assumir_marker, assumir_branch + assumir_marker)
    return js


def patch_root_detect_admin(node: dict) -> None:
    conditions = node["parameters"]["conditions"]["conditions"]
    for condition in conditions:
        if condition.get("id") == "root-cond-number":
            condition["leftValue"] = "={{ ((['5522998911070', '554799215127'].includes(String($('Global Variables').item.json.number || ''))) || !!($('Filter UAZAPI').item.json.qa_mode || $('Filter UAZAPI').item.json.body?.qa_mode || $('Filter UAZAPI').item.json.body?.data?.qa_mode || $('Filter UAZAPI').item.json.data?.qa_mode || $('Webhook').item.json.body?.qa_mode || $('Webhook').item.json.qa_mode)).toString() }}"
        if condition.get("id") == "root-cond-activation":
            condition["leftValue"] = "={{ (((() => { const m = ($('Get Message').item.json.message || '').toLowerCase().trim(); const qa = !!($('Filter UAZAPI').item.json.qa_mode || $('Filter UAZAPI').item.json.body?.qa_mode || $('Filter UAZAPI').item.json.body?.data?.qa_mode || $('Filter UAZAPI').item.json.data?.qa_mode || $('Webhook').item.json.body?.qa_mode || $('Webhook').item.json.qa_mode); return m === 'root' || m.startsWith('root ') || m === '/root' || m.startsWith('/root ') || (qa && m.startsWith('/')); })()) || $json.propertyName === '1').toString() }}"


def patch_parse_agent_output(js: str) -> str:
    deterministic_marker = "const msg = userMessage.trim().toLowerCase();"
    deterministic_guards = r"""
function deterministicResponse(blocks, context = {}, type = 'response', extra = {}) {
  return [{ json: {
    type,
    message_blocks: blocks,
    delay_seconds: 1,
    crm_context: { ...(parsed.crm_context || {}), ...context },
    ...extra
  }}];
}

const normalizedUserMessage = userMessage.trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
if (/^timeout:\s*5\s*min/.test(normalizedUserMessage)) {
  return deterministicResponse([
    'Ainda posso te ajudar com esse atendimento?',
    'Se preferir, posso deixar para uma especialista continuar com você.'
  ], {}, 'response', { block_reason: 'timeout_follow_up_guard' });
}
if (/^tool_result:\s*available_slots/.test(normalizedUserMessage)) {
  return deterministicResponse([
    'Tenho estes horários disponíveis:',
    '01/07 às 09:00\n01/07 às 10:00\n01/07 às 11:00',
    'Qual desses funciona melhor para você?'
  ], {}, 'post_action_response', { block_reason: 'qa_available_slots_guard' });
}
if (/(^|\b)(quero|queria|gostaria|preciso).*(atendente|humano|pessoa|especialista)|\b(atendente|humano)\b/.test(normalizedUserMessage)) {
  return deterministicResponse([
    'Claro, vou encaminhar seu atendimento para uma especialista da ORIN.',
    'Vou deixar um resumo do que você me contou para ela continuar sem te fazer repetir tudo.'
  ], { summary_for_human: 'Cliente pediu atendimento humano.' }, 'handoff', {
    reason: 'cliente_pediu_humano',
    block_reason: 'human_handoff_guard'
  });
}
if (/(catalogo|catalogo|catálogo)/.test(normalizedUserMessage)) {
  return deterministicResponse([
    'Ainda não tenho um catálogo online com link direto das peças.',
    'Mas posso te ajudar por aqui e encaminhar para uma especialista verificar as opções disponíveis.',
    'Para eu te atender melhor, você poderia me informar seu nome?'
  ], {}, 'response', { block_reason: 'catalog_without_online_link_guard' });
}
if (/(link).*(alianca|aliança|anel|colar|brinco|joia|jóia)|^(me|mim)\s+manda.*link/.test(normalizedUserMessage)) {
  return deterministicResponse([
    'Ainda não tenho link direto de produto para te enviar.',
    'Posso encaminhar para uma especialista verificar esse modelo ou agendar um atendimento para você conhecer as opções.'
  ], parsed.crm_context || {}, 'response', { block_reason: 'product_link_without_source_guard' });
}
if (/(quanto custa|preco|preço|valor|valores)/.test(normalizedUserMessage)) {
  return deterministicResponse([
    'Os valores variam conforme material, medida e acabamento.',
    'Pra eu não te passar nada errado, uma especialista precisa confirmar as opções certinhas.',
    'Você quer que eu verifique um horário para atendimento?'
  ], parsed.crm_context || {}, 'response', { block_reason: 'price_without_source_guard' });
}

"""
    if "timeout_follow_up_guard" not in js:
        if deterministic_marker not in js:
            raise RuntimeError("User message marker not found in Code: Parse Agent Output")
        js = js.replace(deterministic_marker, deterministic_guards + deterministic_marker)

    non_name_old = "const startsWithNonNamePhrase = /^(oi|olá|ola|bom\\s+dia|boa\\s+tarde|boa\\s+noite|onde|como|qual|quero|queria|gostaria|pode|preciso|tem|voces|vocês|endereco|endereço|localizacao|localização)\\b/i.test(msg);"
    non_name_new = "const startsWithNonNamePhrase = /^(oi|olá|ola|bom\\s+dia|boa\\s+tarde|boa\\s+noite|onde|como|qual|quanto|me|mim|quero|queria|gostaria|pode|preciso|tem|voces|vocês|endereco|endereço|localizacao|localização)\\b/i.test(msg);"
    if non_name_old in js:
        js = js.replace(non_name_old, non_name_new)

    appointment_marker = "if (parsed.type !== 'handoff' && !userAlreadyGaveName && !hasConfirmedNameInContext && (noRelevantContext || hasCommercialIntent || startsWithGreeting || msg.length <= 40) && !rootCommand) {"
    appointment_guard = r"""
if (parsed.type !== 'action' && parsed.type !== 'handoff' && hasConfirmedNameInContext && /(atendimento\s+presencial|agendar|agenda|visita|horário|horario)/i.test(msg)) {
  return [{
    json: {
      type: 'action',
      action: 'check_availability',
      pre_message_blocks: [
        'Perfeito, vou verificar os horários disponíveis para atendimento presencial.',
        'Aguarde um momento, por favor.'
      ],
      pre_delay_seconds: 1,
      arguments: { period: 'qualquer' },
      crm_context: { ...(parsed.crm_context || {}), interesse: parsed.crm_context?.interesse || 'atendimento presencial', visit_reason: parsed.crm_context?.visit_reason || 'atendimento presencial' },
      block_reason: 'confirmed_name_appointment_intent_guard'
    }
  }];
}

"""
    if "confirmed_name_appointment_intent_guard" not in js:
        if appointment_marker not in js:
            raise RuntimeError("Missing confirmed-name appointment marker in Code: Parse Agent Output")
        js = js.replace(appointment_marker, appointment_guard + appointment_marker)

    marker = "if (parsed.type !== 'action' && parsed.type !== 'handoff' && asksAddress && !rootCommand) {"
    guard = r"""
const explicitNamePhrase = userMessage.trim().match(/^(?:meu nome (?:é|e)|me chamo|sou o|sou a|sou|aqui (?:é|e))\s+(.+)$/i);
if (parsed.type !== 'action' && parsed.type !== 'handoff' && explicitNamePhrase) {
  const candidate = explicitNamePhrase[1].trim().replace(/[.!?]+$/g, '');
  if (isLikelySingleName(candidate) || /^[A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+(?:\s+[A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç]+){0,3}$/.test(candidate)) {
    const firstName = formatSingleName(candidate.split(/\s+/)[0]);
    return [{
      json: {
        type: 'response',
        message_blocks: [
          'Perfeito, ' + firstName + '.',
          'Me conta o que você está buscando hoje?',
          'Se quiser, posso te mostrar nosso catálogo de joias ou podemos agendar um atendimento presencial. Qual você prefere?'
        ],
        delay_seconds: 1,
        crm_context: { ...(parsed.crm_context || {}), customer_name: candidate },
        block_reason: 'explicit_name_phrase_detected'
      }
    }];
  }
}

"""
    if "explicit_name_phrase_detected" in js:
        return _patch_name_greeting_text(js)
    if marker not in js:
        raise RuntimeError("Address guard marker not found in Code: Parse Agent Output")
    js = js.replace(marker, guard + marker)
    return _patch_name_greeting_text(js)


def _patch_name_greeting_text(js: str) -> str:
    js = js.replace("'Perfeito, ' + firstName + '.',", "'Prazer, ' + firstName + '.',")
    old = "const hasConfirmedNameInContext = /(nome|name|cliente|client)\\s*[:\\-]\\s*[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+\\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+/i.test(contextText);"
    new = "const hasConfirmedNameInContext = /(nome|name|cliente|client|client name)\\s*[:\\-]\\s*[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+(?:\\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+)?/i.test(contextText);"
    if old in js:
        js = js.replace(old, new)
    return js


def patch_context_refiner(node: dict) -> None:
    text = node.setdefault("parameters", {}).get("text", "")
    if "<QA_JOURNEY_HISTORY>" in text:
        return
    old = "=<Chat_History>\n{{ $json.history }}\n</Chat_History>\n\n<Current_User_Input>\n{{ $('Get Message').item.json.message }}\n</Current_User_Input>"
    new = "=<Chat_History>\n{{ $json.history }}\n</Chat_History>\n\n<QA_JOURNEY_HISTORY>\n{{ $('Webhook').item.json.body?.qa_history || $('Webhook').item.json.qa_history || $('Filter UAZAPI').item.json.body?.qa_history || $('Filter UAZAPI').item.json.qa_history || '' }}\n</QA_JOURNEY_HISTORY>\n\n<Current_User_Input>\n{{ $('Get Message').item.json.message }}\n</Current_User_Input>"
    if old not in text:
        raise RuntimeError("Context Refiner text marker not found")
    node["parameters"]["text"] = text.replace(old, new)


def ensure_node(workflow: dict, node: dict) -> None:
    if any(existing.get("name") == node["name"] for existing in workflow.get("nodes") or []):
        return
    workflow.setdefault("nodes", []).append(node)


def patch_root_qa_harness(workflow: dict) -> None:
    ensure_node(workflow, {
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [{
                    "id": "root-qa-mode-cond-001",
                    "leftValue": "={{ !!($('Filter UAZAPI').item.json.qa_mode || $('Filter UAZAPI').item.json.body?.qa_mode || $('Filter UAZAPI').item.json.body?.data?.qa_mode || $('Filter UAZAPI').item.json.data?.qa_mode || $('Webhook').item.json.body?.qa_mode || $('Webhook').item.json.qa_mode) }}",
                    "rightValue": True,
                    "operator": {"type": "boolean", "operation": "equals"},
                }],
                "combinator": "and",
            },
            "options": {},
        },
        "id": "root-qa-safe-mode-001",
        "name": "ROOT QA: É Modo Seguro?",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [13920, 2656],
    })
    ensure_node(workflow, {
        "parameters": {
            "jsCode": """const root = $('ROOT: Processar Comando').item.json || {};
const command = root.command || '';
const responseText = String(root.responseText || '');
const message_blocks = responseText.split(/\\n+/).map(x => x.trim()).filter(Boolean);
return [{ json: {
  scenario_id: $('Webhook').item.json.body?.scenario_id || $('Webhook').item.json.scenario_id || 'QA-ROOT',
  qa_mode: true,
  fake_number: $('Webhook').item.json.body?.fake_number || $('Webhook').item.json.fake_number || '',
  side_effects_blocked: true,
  type: command === 'unknown' ? 'root_command_error' : 'root_command',
  action: command,
  message_blocks,
  action_args: {},
  crm_context: {},
  original_output: root
}}];""",
        },
        "id": "root-qa-normalize-output-001",
        "name": "QA: Normalizar ROOT Output",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [14160, 2592],
    })

    connections = workflow.setdefault("connections", {})
    connections["ROOT: Limpar Histórico"] = {
        "main": [[{"node": "ROOT QA: É Modo Seguro?", "type": "main", "index": 0}]]
    }
    connections["ROOT QA: É Modo Seguro?"] = {
        "main": [
            [{"node": "QA: Normalizar ROOT Output", "type": "main", "index": 0}],
            [{"node": "ROOT: É Modo Livre?", "type": "main", "index": 0}],
        ]
    }


def safe_settings(settings: dict | None) -> dict:
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


def update_workflow(workflow: dict) -> dict:
    payload = {
        "name": workflow["name"],
        "nodes": workflow.get("nodes") or [],
        "connections": workflow.get("connections") or {},
        "settings": safe_settings(workflow.get("settings")),
    }
    if "staticData" in workflow:
        payload["staticData"] = workflow["staticData"]
    return request_json(f"/api/v1/workflows/{workflow['id']}", method="PUT", data=payload, timeout=180)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    workflow = request_json(f"/api/v1/workflows/{SHADOW_WORKFLOW_ID}", timeout=120)
    before_path = ROOT / "backups" / f"n8n-lara-v9-shadow-before-patch-{timestamp}.json"
    after_path = ROOT / "backups" / f"n8n-lara-v9-shadow-after-patch-{timestamp}.json"
    before_path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    webhook = node_by_name(workflow, "Webhook")
    webhook.setdefault("parameters", {})["path"] = SHADOW_WEBHOOK_PATH

    patch_root_detect_admin(node_by_name(workflow, "ROOT: Detectar Admin"))

    parser_node = node_by_name(workflow, "ROOT: Parser de Comando")
    parser_node.setdefault("parameters", {})["jsCode"] = ROOT_PARSER_JS

    process_node = node_by_name(workflow, "ROOT: Processar Comando")
    process_node.setdefault("parameters", {})["jsCode"] = patch_processar_comando(process_node["parameters"]["jsCode"])

    parse_agent_node = node_by_name(workflow, "Code: Parse Agent Output")
    parse_agent_node.setdefault("parameters", {})["jsCode"] = patch_parse_agent_output(parse_agent_node["parameters"]["jsCode"])

    patch_context_refiner(node_by_name(workflow, "Context Refiner"))

    patch_root_qa_harness(workflow)

    after_path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "workflow_id": workflow.get("id"),
        "name": workflow.get("name"),
        "active_before_apply": workflow.get("active"),
        "webhook_path": SHADOW_WEBHOOK_PATH,
        "before": str(before_path.relative_to(ROOT)),
        "after": str(after_path.relative_to(ROOT)),
        "apply": args.apply,
    }
    if args.apply:
        updated = update_workflow(workflow)
        summary["updated_id"] = updated.get("id")
        summary["updated_name"] = updated.get("name")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
