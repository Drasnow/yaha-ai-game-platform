import html
import json
import re

from app.agent.state import GameDesign, GeneratedFiles
from app.schemas.generate import GenerationAsset


def _safe_text(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    return html.escape(normalized[:500] or "来一局轻松互动小游戏")


def _asset_note(assets: list[GenerationAsset]) -> str:
    if not assets:
        return ""
    first_asset = assets[0]
    return f"<p class=\"asset-note\">已接入参考素材：{html.escape(first_asset.mime_type)}</p>"


def _manifest(design: GameDesign) -> dict[str, object]:
    return {
        "schemaVersion": "1.0",
        "entry": "index.html",
        "title": design.title,
        "description": design.description,
        "files": ["index.html", "style.css", "game.js"],
        "runtime": "iframe-html-v1",
        "template": design.template,
    }


def render_click_challenge(design: GameDesign, prompt: str, assets: list[GenerationAsset]) -> GeneratedFiles:
    safe_prompt = _safe_text(prompt)
    safe_title = _safe_text(design.title)
    asset_note = _asset_note(assets)
    manifest = _manifest(design)
    files = {
        "index.html": f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" /><title>{safe_title}</title><link rel="stylesheet" href="style.css" /></head><body><main class="game-shell"><p class="eyebrow">Yaha Generated Game</p><h1>{safe_title}</h1><p class="prompt">{safe_prompt}</p>{asset_note}<section class="hud"><span>得分 <strong id="score">0</strong></span><span>剩余 <strong id="time">30</strong>s</span></section><button id="target" type="button">点击能量星 +1</button><p id="result" class="result">在 30 秒内尽可能多地点击目标。</p></main><script src="game.js"></script></body></html>""",
        "style.css": f"""body{{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at top,{design.primary_color},#020617);font-family:Arial,'Microsoft YaHei',sans-serif;color:#fff}}.game-shell{{width:min(760px,92vw);padding:42px;border:1px solid rgba(255,255,255,.18);border-radius:30px;background:rgba(15,23,42,.78);box-shadow:0 24px 80px rgba(0,0,0,.38);text-align:center}}.eyebrow{{color:#c4b5fd;text-transform:uppercase;letter-spacing:.18em;font-size:12px}}h1{{font-size:clamp(32px,7vw,58px);margin:8px 0 14px}}.prompt,.asset-note,.result{{color:#cbd5e1;line-height:1.8}}.hud{{display:flex;justify-content:center;gap:18px;margin:24px 0;flex-wrap:wrap}}.hud span{{padding:10px 16px;border-radius:999px;background:rgba(255,255,255,.1)}}button{{margin:18px auto;padding:20px 30px;border:0;border-radius:999px;background:{design.accent_color};color:#111827;font-weight:900;font-size:18px;cursor:pointer;box-shadow:0 12px 30px rgba(250,204,21,.28);transition:transform .12s ease}}button:disabled{{opacity:.55;cursor:not-allowed}}""",
        "game.js": """let score=0;let time=30;const scoreEl=document.getElementById('score');const timeEl=document.getElementById('time');const target=document.getElementById('target');const result=document.getElementById('result');target.addEventListener('click',()=>{score+=1;scoreEl.textContent=String(score);target.style.transform=`translate(${Math.random()*90-45}px,${Math.random()*60-30}px) scale(${1+Math.random()*0.08})`;});const timer=setInterval(()=>{time-=1;timeEl.textContent=String(time);if(time<=0){clearInterval(timer);target.disabled=true;target.textContent='挑战结束';result.textContent=`最终得分 ${score}，点击重新开始可以再挑战一次。`;document.body.addEventListener('click',()=>location.reload(),{once:true});}},1000);""",
        "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2),
    }
    return GeneratedFiles(files=files, manifest=manifest)


def render_quiz_game(design: GameDesign, prompt: str, assets: list[GenerationAsset]) -> GeneratedFiles:
    safe_prompt = _safe_text(prompt)
    safe_title = _safe_text(design.title)
    asset_note = _asset_note(assets)
    manifest = _manifest(design)
    files = {
        "index.html": f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" /><title>{safe_title}</title><link rel="stylesheet" href="style.css" /></head><body><main><p class="eyebrow">Yaha Quiz Agent</p><h1>{safe_title}</h1><p>{safe_prompt}</p>{asset_note}<div id="question"></div><div id="choices"></div><p id="feedback">选择答案开始闯关。</p><p>得分：<strong id="score">0</strong></p></main><script src="game.js"></script></body></html>""",
        "style.css": f"body{{margin:0;min-height:100vh;display:grid;place-items:center;background:linear-gradient(135deg,{design.primary_color},#0f172a);font-family:Arial,'Microsoft YaHei',sans-serif;color:white}}main{{width:min(760px,92vw);padding:40px;border-radius:28px;background:rgba(15,23,42,.82);text-align:center;box-shadow:0 24px 80px rgba(0,0,0,.35)}}.eyebrow{{color:#bfdbfe;letter-spacing:.16em;text-transform:uppercase;font-size:12px}}#question{{font-size:24px;font-weight:800;margin:24px 0}}button{{display:block;width:100%;margin:10px 0;padding:16px;border:0;border-radius:16px;background:{design.accent_color};color:#111827;font-weight:800;cursor:pointer}}p{{color:#dbeafe;line-height:1.7}}",
        "game.js": "const questions=[['这个游戏由什么驱动生成？','AI Agent','硬编码页面','手写数据库'],['生成产物运行在哪里？','iframe sandbox','浏览器插件','系统终端'],['发布后会出现在哪里？','Home 首页','回收站','登录页']];let index=0,score=0;const q=document.getElementById('question');const choices=document.getElementById('choices');const feedback=document.getElementById('feedback');const scoreEl=document.getElementById('score');function render(){if(index>=questions.length){q.textContent='闯关完成';choices.innerHTML='';feedback.textContent=`最终得分 ${score}/${questions.length}`;return;}q.textContent=questions[index][0];choices.innerHTML='';questions[index].slice(1).forEach((choice,i)=>{const btn=document.createElement('button');btn.textContent=choice;btn.onclick=()=>{if(i===0){score+=1;feedback.textContent='回答正确！';}else{feedback.textContent='再想想，正确答案是第一个。';}scoreEl.textContent=String(score);index+=1;setTimeout(render,700);};choices.appendChild(btn);});}render();",
        "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2),
    }
    return GeneratedFiles(files=files, manifest=manifest)


def render_avoid_obstacle(design: GameDesign, prompt: str, assets: list[GenerationAsset]) -> GeneratedFiles:
    safe_prompt = _safe_text(prompt)
    safe_title = _safe_text(design.title)
    asset_note = _asset_note(assets)
    manifest = _manifest(design)
    files = {
        "index.html": f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" /><title>{safe_title}</title><link rel="stylesheet" href="style.css" /></head><body><main><p class="eyebrow">Yaha Dodge Agent</p><h1>{safe_title}</h1><p>{safe_prompt}</p>{asset_note}<canvas id="game" width="640" height="360"></canvas><p id="hint">使用方向键躲避红色障碍，坚持越久分数越高。</p></main><script src="game.js"></script></body></html>""",
        "style.css": f"body{{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle,{design.primary_color},#020617);font-family:Arial,'Microsoft YaHei',sans-serif;color:white}}main{{width:min(820px,94vw);padding:34px;border-radius:28px;background:rgba(15,23,42,.82);text-align:center;box-shadow:0 24px 80px rgba(0,0,0,.35)}}.eyebrow{{color:#fecaca;letter-spacing:.16em;text-transform:uppercase;font-size:12px}}canvas{{max-width:100%;border-radius:20px;background:#0f172a;border:1px solid rgba(255,255,255,.18)}}p{{color:#e2e8f0;line-height:1.7}}",
        "game.js": "const canvas=document.getElementById('game');const ctx=canvas.getContext('2d');const player={x:300,y:170,size:26};let obstacle={x:620,y:Math.random()*320,size:28,speed:3};let score=0;let alive=true;const keys={};addEventListener('keydown',e=>keys[e.key]=true);addEventListener('keyup',e=>keys[e.key]=false);function loop(){ctx.clearRect(0,0,640,360);if(keys.ArrowUp)player.y-=5;if(keys.ArrowDown)player.y+=5;if(keys.ArrowLeft)player.x-=5;if(keys.ArrowRight)player.x+=5;player.x=Math.max(0,Math.min(614,player.x));player.y=Math.max(0,Math.min(334,player.y));obstacle.x-=obstacle.speed;if(obstacle.x<-30){obstacle={x:640,y:Math.random()*330,size:28,speed:3+score/300};}score+=1;ctx.fillStyle='#22c55e';ctx.fillRect(player.x,player.y,player.size,player.size);ctx.fillStyle='#ef4444';ctx.beginPath();ctx.arc(obstacle.x,obstacle.y,obstacle.size,0,Math.PI*2);ctx.fill();ctx.fillStyle='white';ctx.font='20px Arial';ctx.fillText('Score '+score,20,32);if(Math.abs(player.x-obstacle.x)<34&&Math.abs(player.y-obstacle.y)<34){alive=false;ctx.fillText('Game Over - click to restart',210,180);}if(alive)requestAnimationFrame(loop);}canvas.onclick=()=>location.reload();loop();",
        "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2),
    }
    return GeneratedFiles(files=files, manifest=manifest)


TEMPLATE_RENDERERS = {
    "click_challenge": render_click_challenge,
    "quiz_game": render_quiz_game,
    "avoid_obstacle": render_avoid_obstacle,
}
