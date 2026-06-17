// Connect round: clean hint toggle + lenient grading + inline feedback.
window.onload = function () {

  /* ---------- lenient answer matching (deterministic, no LLM) ---------- */
  function _normAns(s){ return (s||"").toLowerCase().replace(/[^a-z0-9\s]/g," ").replace(/\s+/g," ").trim(); }
  function _lev(a,b){
    var m=a.length,n=b.length,i,j; if(!m)return n; if(!n)return m;
    var prev=[],cur=[]; for(j=0;j<=n;j++)prev[j]=j;
    for(i=1;i<=m;i++){ cur[0]=i; for(j=1;j<=n;j++){ var c=a.charAt(i-1)===b.charAt(j-1)?0:1; cur[j]=Math.min(cur[j-1]+1,prev[j]+1,prev[j-1]+c);} var t=prev;prev=cur;cur=t; }
    return prev[n];
  }
  function _sim(a,b){ var ml=Math.max(a.length,b.length); return ml===0?1:(1-_lev(a,b)/ml); }
  function looseMatch(userRaw, correctRaw){
    var u=_normAns(userRaw), c=_normAns(correctRaw);
    if(!u||!c) return false;
    if(u===c) return true;
    var ml=Math.max(u.length,c.length);
    var threshold = ml<=4?0.75:(ml<=8?0.80:0.82);
    if(_sim(u,c)>=threshold) return true;
    if(_sim(u.split(" ").sort().join(" "), c.split(" ").sort().join(" "))>=threshold) return true;
    var stop={a:1,an:1,the:1,of:1,is:1,are:1,and:1,to:1,in:1,on:1,by:1,for:1,with:1};
    var cw=c.split(" ").filter(function(w){return w&&!stop[w];});
    var uw=u.split(" ").filter(Boolean);
    if(cw.length){ if(cw.every(function(x){return uw.some(function(y){return y===x||_sim(y,x)>=0.8;});})) return true; }
    return false;
  }
  function soundex(s){
    var a=s.toLowerCase().split(''),f=a.shift(),r='',codes={a:'',e:'',i:'',o:'',u:'',b:1,f:1,p:1,v:1,c:2,g:2,j:2,k:2,q:2,s:2,x:2,z:2,d:3,t:3,l:4,m:5,n:5,r:6};
    r=f+a.map(function(v){return codes[v];}).filter(function(v,i,a){return ((i===0)?v!==codes[f]:v!==a[i-1]);}).join('');
    return (r+'000').slice(0,4).toUpperCase();
  }
  function gradeAnswer(answer, correctAnswer){
    var commands=(correctAnswer||"").split(";");
    for (var k=0;k<commands.length;k++){
      var command=commands[k]; if(!command) continue;
      var orCommands=command.indexOf(":")!==-1?command.split(":"):[command];
      var results=[];
      for (var i=0;i<orCommands.length;i++){
        var cmd=orCommands[i];
        if (cmd.charAt(0)==="/"){
          if (cmd.charAt(1)==="#"){ results.push(soundex(answer.toLowerCase())===soundex(cmd.replace("#","").replace("/","").toLowerCase())?1:0); }
          else if (cmd.charAt(1)==="?"){ results.push(answer===cmd.replace("?","").replace("/","")?1:0); }
          else if (cmd.charAt(1)==="="){ results.push(_normAns(answer)===_normAns(cmd.replace("=","").replace("/",""))?1:0); }
          else { results.push(looseMatch(answer, cmd.replace("/",""))?1:0); }
        } else if (cmd.charAt(0)===","){
          var body=cmd.slice(2).toLowerCase(), aw=answer.toLowerCase().split(" "), cwds=body.split(" ");
          if (cmd.charAt(1)==="#"){ results.push(aw.map(soundex).toString().indexOf(cwds.map(soundex).toString())!==-1?1:0); }
          else { results.push(cwds.every(function(w){return aw.indexOf(w)!==-1;})?1:0); }
        }
      }
      if (results.indexOf(1)!==-1) return true;
    }
    return false;
  }

  /* ---------- elements ---------- */
  var ta      = document.getElementById("commentsss");
  var cq      = document.getElementById("cquestion");
  var hintBtn = document.getElementById("hintbutton");
  var hint    = document.getElementById("hinthere");
  var feedback= document.getElementById("asdactivecorrect");
  var verdict = document.getElementById("asdCorrectOrNot");
  var nextBtn = document.getElementById("buttoon");
  var prevBtn = document.getElementById("buttoon2");
  if (!ta || !cq) return;
  var qid   = cq.getAttribute("data-qid");
  var round = cq.getAttribute("data-round") || "connect";   // "connect" or "av"

  /* hint toggle (no jumping, no border-size change) */
  if (hintBtn && hint){
    hint.style.display = "none";
    hintBtn.addEventListener("click", function(e){
      e.preventDefault();
      var showing = hint.style.display !== "none";
      hint.style.display = showing ? "none" : "block";
      hintBtn.classList.toggle("active", !showing);
    });
  }

  /* navigation */
  function curNumber(){ var m=String(location.href).replace(/\/$/,'').match(/(\d+)$/); return m?parseInt(m[1]):1; }
  function go(d){ var base=String(location.href).replace(/\/$/,'').replace(/\d+$/,''); location.href=base+(curNumber()+d); }
  function showNav(){
    var n=curNumber();
    if (nextBtn && n < parseInt(nextBtn.getAttribute("data-attr"))-1) nextBtn.style.display="inline-flex";
    if (prevBtn && n > 1) prevBtn.style.display="inline-flex";
  }
  if (nextBtn) nextBtn.onclick=function(){ if(curNumber() < parseInt(nextBtn.getAttribute("data-attr"))-1) go(1); };
  if (prevBtn) prevBtn.onclick=function(){ if(curNumber()>1) go(-1); };

  /* submit / reveal */
  var answered=false;
  function reveal(correct, answer){
    if (answered) return; answered=true;
    if (verdict) verdict.innerHTML = correct ? "Correct!" : "Wrong";
    if (feedback){ feedback.classList.add(correct?"is-correct":"is-wrong"); feedback.style.display="block"; }
    if (window.flashGlow) window.flashGlow(correct);
    if (window.recordScore && qid) window.recordScore({mode: round, qid: qid, answer: answer || ""});
    showNav();
  }
  ta.addEventListener("keypress", function(e){
    if ((e.which||e.keyCode)!==13 || e.shiftKey) return;
    e.preventDefault();
    if (answered){ ta.value=""; return; }
    var answer = ta.value;
    reveal(gradeAnswer(answer, cq.getAttribute("data-answer") || ""), answer);
    ta.value="";
  });
};
