const fs=require('fs'),path=require('path');
const html=fs.readFileSync(path.join(__dirname,'../../ui/index.html'),'utf8');
const code=html.split('/*IMAGE-DOWNLOAD-START*/')[1].split('/*IMAGE-DOWNLOAD-END*/')[0];
let fail=0;const ok=(c,m)=>{console.log(c?'ok  ':'FAIL',m);if(!c)fail++};
const els={downloadFormat:{value:'png'},downloadFormatStatus:{textContent:''}}, $=id=>els[id];
const clicks=[],calls=[];let response={image:'data:image/webp;base64,AAAA'};
const document={createElement:()=>({click(){clicks.push([this.href,this.download])}})};
const J={method:'POST'};const api=async(url,opt)=>{calls.push([url,JSON.parse(opt.body)]);if(response instanceof Error)throw response;return response};
const T=new Function('$','document','api','J',code+';return {dl,downloadImage}')($,document,api,J);
(async()=>{
 const png='data:image/png;base64,AAAA';
 await T.dl(1,png,5);ok(clicks[0][0]===png&&clicks[0][1]==='sprite_5_1x.png'&&!calls.length,'PNG default unchanged');
 els.downloadFormat.value='webp';await T.dl(8,png,5);
 ok(calls[0][0]==='/api/export/webp'&&calls[0][1].scale===8&&calls[0][1].image===png,'WebP posts original PNG and requested scale');
 ok(clicks[1][0]===response.image&&clicks[1][1]==='sprite_5_8x.webp','WebP filename and actual MIME');
 response={image:png};await T.downloadImage(png,'asset');ok(clicks.length===2&&els.downloadFormatStatus.textContent.includes('Invalid WebP'),'no mislabeled PNG fallback');
 response=new Error('encoder unavailable');await T.downloadImage(png,'asset');ok(clicks.length===2&&els.downloadFormatStatus.textContent.includes('encoder unavailable'),'encoder error is visible');
 console.log(fail?'FAILED':'ALL PASSED');process.exit(fail?1:0);
})().catch(e=>{console.error(e);process.exit(1)});
