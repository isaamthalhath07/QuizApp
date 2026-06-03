window.onload = function(){
var myLink = document.getElementById('buttoon');
var prevButton = document.getElementById("buttoon2");
prevButton.onclick = function(){
    link = (String(window.location.href).substring(0, String(window.location.href).length - 1) + String(parseInt(String(window.location.href).substr(String(window.location.href).length - 5).match(/\d/g).join("")) -1));//fix this kid
    console.log(link);
    window.location.href=link;


}

myLink.onclick = function(){
    elem = this.getAttribute("data-attr");
    link = (String(window.location.href).substring(0, String(window.location.href).length - 1) + String(parseInt(String(window.location.href).substr(String(window.location.href).length - 5).match(/\d/g).join("")) + 1));

    if(parseInt(String(window.location.href).substr(String(window.location.href).length - 5).match(/\d/g).join("")) < parseInt(elem) - 1){
         window.location.href=link;
        }




    console.log(link);


}
is_clicked = false;
button = document.getElementById('hintbutton');
$(document.getElementById("asdactivecorrect")).hide();

button.onclick = function(){


    if (is_clicked != true){
     if ( $('#hinthere').css('visibility') == 'hidden' ){
    $('#hinthere').css('visibility','visible');}
  else{
    $('#hinthere').css('visibility','hidden');}

    $(button).css('background','linear-gradient(90deg, rgba(240,36,36,1) 0%, rgba(255,72,0,1) 100%)');
    $(button).css('border','10px solid red');

    }

    is_clicked = true;


}
// --- Lenient answer matching (deterministic, no LLM) ---
function _normAns(s){
    return (s||"").toLowerCase()
        .replace(/[^a-z0-9\s]/g," ")
        .replace(/\s+/g," ")
        .trim();
}
function _lev(a,b){
    var m=a.length,n=b.length,i,j;
    if(!m) return n; if(!n) return m;
    var prev=[],cur=[];
    for(j=0;j<=n;j++) prev[j]=j;
    for(i=1;i<=m;i++){
        cur[0]=i;
        for(j=1;j<=n;j++){
            var cost=a.charAt(i-1)===b.charAt(j-1)?0:1;
            cur[j]=Math.min(cur[j-1]+1, prev[j]+1, prev[j-1]+cost);
        }
        var t=prev; prev=cur; cur=t;
    }
    return prev[n];
}
function _sim(a,b){ var ml=Math.max(a.length,b.length); return ml===0?1:(1-_lev(a,b)/ml); }
function looseMatch(userRaw, correctRaw){
    var u=_normAns(userRaw), c=_normAns(correctRaw);
    if(!u || !c) return false;
    if(u===c) return true;
    var ml=Math.max(u.length,c.length);
    var threshold = ml<=4 ? 0.75 : (ml<=8 ? 0.80 : 0.82);
    if(_sim(u,c) >= threshold) return true;
    if(_sim(u.split(" ").sort().join(" "), c.split(" ").sort().join(" ")) >= threshold) return true;
    var stop={a:1,an:1,the:1,of:1,is:1,are:1,and:1,to:1,in:1,on:1,by:1,for:1,with:1};
    var cw=c.split(" ").filter(function(w){ return w && !stop[w]; });
    var uw=u.split(" ").filter(Boolean);
    if(cw.length){
        var all=cw.every(function(x){
            return uw.some(function(y){ return y===x || _sim(y,x)>=0.8; });
        });
        if(all) return true;
    }
    return false;
}

function soundex(s){
    var a = s.toLowerCase().split(''),
        f = a.shift(),
        r = '',
        codes = { a: '', e: '', i: '', o: '', u: '', b: 1, f: 1, p: 1, v: 1, c: 2, g: 2, j: 2, k: 2, q: 2, s: 2, x: 2, z: 2, d: 3, t: 3, l: 4, m: 5, n: 5, r: 6 };

    r = f +
        a
        .map(function(v, i, a) {
            return codes[v]
        })
        .filter(function(v, i, a) {
            return ((i === 0) ? v !== codes[f] : v !== a[i - 1]);
        })
        .join('');

    return (r + '000').slice(0, 4).toUpperCase();
};
function submitOnEnter(){
  if(!(($(document.getElementById("asdactivecorrect"))).is(":hidden"))){
        event.preventDefault(); // Prevents the addition of a new line in the text field (not needed in a lot of cases)
        event.target.value = "";


  }
  if(event.which === 13 && !event.shiftKey){
        console.log("BRAH HE ANSWERED POGGERS");

        answer = event.target.value;
        correctAnswer = document.getElementById("cquestion").getAttribute("data-answer");

        commands = correctAnswer.split(";");
        console.log(commands);
        for (var i = 0; i < commands.length; i++) {
                command = commands[i];
                var orCommands;
                var orResults = [];
                if (command.includes(":")){// ":" means or soo thats a thing we need to deal with idk how me gunna deal with "&" tho
                    orCommands = command.split(":");

                }
                else{
                    orCommands = command;

                }
                for (var i = 0; i < orCommands.length; i++) {
                console.log(orCommands);
                if(orCommands[i].charAt(0) === "/"){ //If command is strating with / then make sure these words are the answer
                    if(orCommands[i].charAt(1) === "#"){// If commands starts with # that means it accepts spelling mistakes
                        if(soundex(answer.toLowerCase()) === soundex(orCommands[i].replace("#", "").replace("/", "").toLowerCase())){
                           console.log("CORRECT ANSWER (SOUNDEX APPROVED)");
                           orResults.push(1);


                    }
                    else{
                        orResults.push(0);
                    }}
                    if(orCommands[i].charAt(1) === "?"){
                        if(answer === orCommands[i].replace("?", "").replace("/", "")){
                        console.log("CORRECT ANSWER (? APPROVED)");
                        orResults.push(1);


                    }
                    else{
                        orResults.push(0);
                    }}
                    if(orCommands[i].charAt(1) !== "#" && orCommands[i].charAt(1) !== "?"){// If commands starts with # that means it accepts spelling mistakes
                        if(looseMatch(answer, orCommands[i].replace("/", ""))){
                        console.log("CORRECT ANSWER (normal APPROVED)");
                        orResults.push(1);


                    }
                    else{
                        orResults.push(0);
                    }}





                }
				if(orCommands[i].charAt(0) === "!"){



                    if(orCommands[i].charAt(1) === "?"){
                        if(answer.includes(orCommands[i].replace("?", "").replace("!", ""))){
                        console.log("RETRY (!?)");



                    }
                    }
                    if(orCommands[i].charAt(1) !== "#" && orCommands[i].charAt(1) !== "?"){// If commands starts with # that means it accepts spelling mistakes
                        if(answer.toLowerCase().includes(orCommands[i].replace("!", "").toLowerCase())){
                        console.log("RETRY (!)");



                    }
                  }}
                if(orCommands[i].charAt(0) === ","){//contains some sentences


                    if(orCommands[i].charAt(1) === "#"){// If commands starts with # that means it accepts spelling mistakes
                        var correct = orCommands[i].replace("#", "").replace(",", "").toLowerCase();
                        var answer_words = answer.split(" ");
                        var correct_words = correct.split(" ");
                        var soundex_correct_words =  correct_words.map(soundex).toString();
                        var soundex_answer_words = answer_words.map(soundex).toString();
                        console.log(soundex_correct_words);
                        console.log(soundex_answer_words);
                        console.log(correct_words);
                        console.log(answer_words.map(soundex));

                        if(soundex_answer_words.includes(soundex_correct_words) == true){
                            orResults.push(1);
                        }
                        else{
                        orResults.push(0);
                        console.log(soundex_answer_words.includes(soundex_correct_words));}







                        }
                        if(orCommands[i].charAt(1) === "@"){// If commands starts with # that means it accepts spelling mistakes
                        var correct = orCommands[i].replace("@", "").replace(",", "").toLowerCase();
                        var answer_words = answer.toLowerCase().split(" ");
                        var correct_words = correct.toLowerCase().split(" ");
                        var soundex_correct_words =  correct_words.toString();
                        var soundex_answer_words = answer_words.toString();
                        console.log(soundex_correct_words);
                        console.log(soundex_answer_words);
                        if(soundex_answer_words.includes(soundex_correct_words) == true){
                            orResults.push(1);
                        }
                        else{
                        orResults.push(0);
                        console.log(soundex_answer_words.includes(soundex_correct_words));}








                        }
                        if(orCommands[i].charAt(1) === "$"){// If commands starts with $ it dosent search for consecutive string searchs each word differently and if that word is there then it allows unlike the # one
                        var correct = orCommands[i].replace("$", "").replace(",", "").toLowerCase();
                        var answer_words = answer.split(" ");
                        var correct_words = correct.split(" ");
                        var soundex_correct_words =  correct_words.map(soundex);
                        var soundex_answer_words = answer_words.map(soundex);
                        console.log(soundex_correct_words);
                        console.log(soundex_answer_words);
                        var check = soundex_correct_words.every(i => soundex_answer_words.includes(i));
                        if(check == true){
                            orResults.push(1);
                        }
                        else{
                        orResults.push(0);
                        }
                        }
                        if(orCommands[i].charAt(1) === "?"){// Searches if certain words are in a sentence (not case sensitive)
                        var correct = orCommands[i].replace("?", "").replace(",", "").toLowerCase();
                        var answer_words = answer.toLowerCase().split(" ");
                        var correct_words = correct.split(" ");

                        console.log(correct_words);
                        console.log(answer_words);
                        var check = correct_words.every(i => answer_words.includes(i));
                        if(check == true){
                            orResults.push(1);
                        }
                        else{
                        orResults.push(0);
                        console.log(check);}
                        }
                        if(orCommands[i].charAt(1) === "%"){//Searches if certain words are in a sentence case sensitive
                        var correct = orCommands[i].replace("%", "").replace(",", "");
                        var answer_words = answer.split(" ");
                        var correct_words = correct.split(" ");

                        console.log(correct_words);
                        console.log(answer_words);
                        var check = correct_words.every(i => answer_words.includes(i));
                        if(check == true){
                            orResults.push(1);
                        }
                        else{
                        orResults.push(0);
                        console.log(check);}
                        }


                }




                }
                if (orResults.includes(1) && orResults){
                    // Prevents the addition of a new line in the text field (not needed in a lot of cases)
                $(document.getElementById("asdactivecorrect")).show();
                document.getElementById("asdactivecorrect").style.background = "linear-gradient(90deg, rgba(6,184,0,1) 0%, rgba(7,117,0,1) 100%)";

                document.getElementById("asdCorrectOrNot").innerHTML = "Correct!";
                console.log("correct birch");
                 $(document.getElementById("buttoon")).fadeIn(200);
                    if(parseInt(String(window.location.href).substr(String(window.location.href).length - 5).match(/\d/g).join("")) > 1){

        $(document.getElementById("buttoon2")).fadeIn(200);//Next buttons and previous buttons display
        }
                result = 1;
                event.preventDefault(); // Prevents the addition of a new line in the text field (not needed in a lot of cases)
        event.target.value = "";


                }
                if(orResults.includes(1) == false && orResults){
                $(document.getElementById("asdactivecorrect")).show();
                                document.getElementById("asdactivecorrect").style.background = "linear-gradient(90deg, rgba(184,0,0,1) 0%, rgba(117,0,0,1) 100%)";
                                 document.getElementById("asdCorrectOrNot").innerHTML = "Wrong";
                console.log("IMAGINE BEING BAD AND GETTING AN ANSWER WRONG LONL");
                 $(document.getElementById("buttoon")).fadeIn(200);
                    if(parseInt(String(window.location.href).substr(String(window.location.href).length - 5).match(/\d/g).join("")) > 1){

        $(document.getElementById("buttoon2")).fadeIn(200);//Next buttons and previous buttons display
        }
                }


  }
        event.preventDefault(); // Prevents the addition of a new line in the text field (not needed in a lot of cases)
        event.target.value = "";




        }




}
document.getElementById("commentsss").addEventListener("keypress", submitOnEnter);
}
