"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;

const fs = require("fs");
// import {PythonShell} from 'python-shell';
let list = [];
let kwd = [];
let package1 = "";
let toShow = [];
let msg = [];

function isNotLetter(c) {
    ///return true;
    //console.log(c);
    return c.toLowerCase() == c.toUpperCase();
  }

// eslint-disable-next-line @typescript-eslint/naming-convention
let Keyword_list = ["seaborn", "sklearn", "matplotlib", "deprecate"];
function getDeprecatedAPIcall(currentLine, apiElements,lineNo) {

    //console.log(currentLine);
    currentLine = currentLine.trim();
    //console.log(currentLine);
    if(currentLine.indexOf("#") !== -1){
        currentLine = currentLine.substring(0, currentLine.indexOf("#"));
    }
    //console.log(currentLine);
    apiElements.forEach(element => {
        let words = currentLine.split("=");
        let elements = element.split(":");
        let str = elements[0].replace("()", "");
        //console.log(words);
        //console.log(str,words,elements,currentLine,"\n","***********************");
        if (words[words.length - 1].indexOf(str) !== -1 && str !== "") {
            let startInd=words[words.length - 1].indexOf(str);
            let endInd=startInd+str.length;
            let flagForRealFunc= false;
            for(let i=endInd;i<words[words.length - 1].length;i++){
                if(words[words.length - 1][i]==" " ){
                    continue;
                }

                else if(words[words.length - 1][i]=="(" ){
                    flagForRealFunc=true;
                    break;
                }
                else {
                    break;
                }
            }


            if (elements.length !== 0 && flagForRealFunc && ((startInd>0 && isNotLetter(words[words.length - 1].charAt(startInd-1)) && isNaN(words[words.length - 1].charAt(startInd-1)) && words[words.length - 1].charAt(startInd-1)!='_' ) || startInd==0) && ((endInd<words[words.length - 1].length-1 &&  isNotLetter(words[words.length - 1].charAt(endInd))  && isNaN(words[words.length - 1].charAt(endInd)) && words[words.length - 1].charAt(endInd)!='_' ) || endInd==words[words.length - 1].length-1)) {
                let flag = 1;
                //console.log(str,elements);
                Keyword_list.forEach(element1 => {
                    if (elements[0].indexOf(element1) !== -1) {
                        flag = 0;
                    }
                });
                if (flag !== 0) {
                    const str1 = elements[0].replace("()", "");
                    if (!kwd.includes(str1) || true){
                        kwd.push(str1);
                        let msg1 = elements[1];
                        if(msg1!= undefined){
                            
                        if ( msg1.indexOf("arg") !== -1) {
                            msg1 = `${elements[0]} : arguments has been deprecated"`;
                        }
                        else {
                            msg1 = `${elements[0]} has been deprecated. `;
                        }
                        for (let i = 1; i < elements.length; i++) {
                            msg1 += elements[i] + " ";
                        }
                        if (!msg.includes(msg1)) {
                            msg.push(msg1);
                        }
                        if(!toShow.includes("At Line number - "+lineNo+" , " +str1+" - "+msg1)){
                            toShow.push("At Line number - "+lineNo+" , " +str1+" - "+msg1);
                        }
                    }
                    }
                }
            }
        }
    });
}
function readContents(currentLine) {
    // eslint-disable-next-line @typescript-eslint/naming-convention
    function util_readContents(fp1) {
        let str1 = fs.readFileSync(fp1, 'utf8');
        let list1 = str1.split("\n");
        // console.log(list1);
        list1.forEach(element => {
            if (!list.includes(element)) {
                list.push(element);
            }
        });
    }
    const packages = ["sklearn", "pandas", "numpy", "scipy", "seaborn", "matplotlib","keras","theano","tk"];
    if (currentLine.indexOf("import") !== -1) {
        for (let i = 0; i < packages.length; i++) {
            if (currentLine.indexOf(packages[i]) !== -1) {
                let path = require('path');
                let fp1 = path.join(__dirname, "/out/" + packages[i] + "_deprecated_api_elements.txt");
                util_readContents(fp1);
                package1 = packages[i];
            }
            
        }
    }
}

// exports.activate = activate;
// function deactivate() { }
// exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map


async function myRead(){
    let path = require('path');
    let fp1 = path.join(__dirname, "body.txt");
    let str1 = fs.readFileSync(fp1, 'utf8');
    let list1 = str1.split("\n");
    //console.log(list1);
    for (let i = 0; i < list1.length; i++) {
        // let text = editor.document.lineAt(i).text;
        readContents(list1[i]); 
        getDeprecatedAPIcall(list1[i], list,i+1);
        // console.log("here1 - ",kwd,msg);
        continue;
    }
    //console.log(list)
    //console.log(kwd,msg);
    //console.log(kwd,msg,list);

}

//myRead();


const express = require('express');
const bodyParser = require('body-parser');
const ejs = require('ejs');



const app = express();
const port = 3000;
app.set('view engine', 'ejs');
app.use(express.static(__dirname + '/public'));
app.use(bodyParser.urlencoded({extended :true}))
app.get('/', (req, res) => {
    res.sendFile(__dirname + '/index.html');
});

app.post('/submit', async(req, res) => {
    list = []
    kwd = [];
    package1 = "";
    msg = [];
    toShow = [];
    // we write body to a file

    fs.writeFileSync('body.txt', req.body.file);
    await myRead();
    //console.log(kwd,msg);
    res.render('result.ejs', {toShow: toShow});
})

app.listen(port, () => {
    console.log(`Example app listening at http://localhost:${port}`);
});