/* Execute the unchanged locked TypeScript compiler with a read-only JSC host.
 * No declarations are stubbed and no diagnostics are filtered. This is an
 * alternate-host type check, not an npm/Vite build or browser acceptance.
 * `typeInput` is a manifest filename supplied with the jsc -e option.
 */
var input=JSON.parse(readFile(typeInput));
if(typeof typeRoots!=="undefined"){for(var root of typeRoots)if(input.rootNames.indexOf(root)<0)throw Error("Unknown root file");input.rootNames=typeRoots;}
load(input.compilerFile);
var files=new Set(input.files),dirs=new Set(input.directories);
function path(name){return ts.getNormalizedAbsolutePath(name,input.cwd);}
function readText(name){name=path(name);return files.has(name)?readFile(name):undefined;}
var converted=ts.convertCompilerOptionsFromJson(input.compilerOptions,input.projectDirectory);
var options=converted.options;
// parseJsonConfigFileContent normally supplies this non-public resolver field.
// convertCompilerOptionsFromJson alone does not; without it relative `paths`
// silently fall back to the original package instead of the verified copy.
if(options.paths&&!options.baseUrl)options.pathsBasePath=input.projectDirectory;
var parsedFiles=0;
var host={
 getSourceFile:function(name,version,onError){var text=readText(name);if(text===undefined)return undefined;if(typeof typeTrace!=="undefined"&&typeTrace){print(JSON.stringify({stage:"read",file:name}));if(/\/core\/index\.d\.ts$/.test(name)){print('TRACE STOP: original barrel reached');quit(2);}}var parseOptions=typeof version==='object'?Object.assign({},version):{languageVersion:version};parseOptions.jsDocParsingMode=ts.JSDocParsingMode.ParseForTypeErrors;var source=ts.createSourceFile(name,text,parseOptions);if(++parsedFiles%100===0){print(JSON.stringify({stage:"parse",sourceFiles:parsedFiles}));gc();}return source;},
 getDefaultLibFileName:function(options){return input.compilerLib+'/'+ts.getDefaultLibFileName(options);},
 getDefaultLibLocation:function(){return input.compilerLib;},
 writeFile:function(){throw Error('This host is read-only');},
 getCurrentDirectory:function(){return input.cwd;},
 getDirectories:function(name){name=path(name);return input.directories.filter(function(d){return ts.getDirectoryPath(d)===name;}).map(function(d){return ts.getBaseFileName(d);});},
 getCanonicalFileName:function(name){return name;},
 useCaseSensitiveFileNames:function(){return true;},
 getNewLine:function(){return '\n';},
 fileExists:function(name){return files.has(path(name));},
 readFile:readText,
 directoryExists:function(name){return dirs.has(path(name));},
 realpath:path
};
var program=ts.createProgram(input.rootNames,options,host);
print(JSON.stringify({stage:"program-created",sourceFiles:program.getSourceFiles().length}));gc();
if(typeof typeTrace!=="undefined"&&typeTrace){print('TRACE ONLY: no type acceptance');quit();}
var checkedFiles=typeof typeCheckFiles!=="undefined"?typeCheckFiles:null;
if(checkedFiles)for(var file of checkedFiles)if(input.rootNames.indexOf(file)<0)throw Error('Unknown diagnostic root');
var diagnostics;
if(checkedFiles){
 diagnostics=converted.errors.concat(program.getOptionsDiagnostics(),program.getGlobalDiagnostics(),program.getSyntacticDiagnostics());gc();
 for(var file of checkedFiles){diagnostics=diagnostics.concat(program.getSemanticDiagnostics(program.getSourceFile(file)));gc();}
}else diagnostics=converted.errors.concat(ts.getPreEmitDiagnostics(program));
for(var diagnostic of diagnostics){var at=diagnostic.file&&diagnostic.start!==undefined?diagnostic.file.getLineAndCharacterOfPosition(diagnostic.start):null;print(JSON.stringify({category:ts.DiagnosticCategory[diagnostic.category],code:diagnostic.code,file:diagnostic.file?diagnostic.file.fileName:null,line:at?at.line+1:null,character:at?at.character+1:null,message:ts.flattenDiagnosticMessageText(diagnostic.messageText,'\n')}));}
print(JSON.stringify({compilerVersion:ts.version,rootFiles:input.rootNames.length,sourceFiles:program.getSourceFiles().length,checkedFiles:checkedFiles,diagnostics:diagnostics.length,strict:options.strict,skipLibCheck:options.skipLibCheck,noEmit:options.noEmit,jsDocParsingMode:'ParseForTypeErrors (compiler default)',host:'JavaScriptCore read-only file manifest; locked TypeScript compiler, import-normalized original declarations where configured'}));
// jsc ignores the argument to quit(). Throw after recording every diagnostic so
// an erroneous check cannot produce a successful process exit.
if(diagnostics.length)throw Error('Type diagnostics: '+diagnostics.length);
quit();
