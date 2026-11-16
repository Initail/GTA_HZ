// Loading the landing page does not initialize WebGL. The user starts the city.
const button=document.querySelector<HTMLButtonElement>('#enter-city')!;
button.addEventListener('click',async()=>{
 button.disabled=true;
 document.querySelector<HTMLElement>('#welcome')!.hidden=true;
 const runtime='/runtime/main.js?v=0.16.0-rc.3';
 try{await import(/* @vite-ignore */ runtime);}
 catch(error){
  document.querySelector<HTMLElement>('#welcome')!.hidden=false;
  document.querySelector<HTMLElement>('#entry-error')!.textContent='启动失败，请检查资源是否下载完整，然后刷新重试。'+String(error);
 }
},{once:true});
