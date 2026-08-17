    // client facing part of extension, creates WSRPC client (jsx cannot
    // do that)
    // consumes RPC calls from server (OpenPype) calls ./host/index.jsx and
    // returns values back (in json format)
    
    const os = require('os');
    const home_dir = os.homedir()
    var CEP_LOG_DIR = home_dir + '/.ayon/'
    var CEP_LOG_FILE = CEP_LOG_DIR + 'ayon_animate_cep_client.log';


    function stringifyLogPart(value) {
      if (typeof value === 'string') {
        return value;
      }
      try {
        return JSON.stringify(value);
      } catch (e) {
        return String(value);
      }
    }

    function appendCepLog(level, args) {
      try {
        if (!window.cep || !window.cep.fs) {
          return;
        }

        window.cep.fs.makedir(CEP_LOG_DIR);

        var parts = [];
        for (var i = 0; i < args.length; i++) {
          parts.push(stringifyLogPart(args[i]));
        }

        var line = '[' + (new Date()).toISOString() + '] [' + level + '] ' + parts.join(' ') + '\n';
        var existing = window.cep.fs.readFile(CEP_LOG_FILE);
        var content = '';
        if (existing && existing.err === 0 && typeof existing.data === 'string') {
          content = existing.data;
        }
        window.cep.fs.writeFile(CEP_LOG_FILE, content + line);
      } catch (_) {
        // Last-resort: never throw from logger path.
      }
    }

    var __console = (typeof console !== 'undefined') ? console : null;
    var __consoleWarn = (__console && __console.warn) ? __console.warn.bind(__console) : null;
    var __consoleInfo = (__console && __console.info) ? __console.info.bind(__console) : null;
    var __consoleDebug = (__console && __console.debug) ? __console.debug.bind(__console) : null;
    var __consoleError = (__console && __console.error) ? __console.error.bind(__console) : null;

    if (__console) {
      __console.warn = function() {
        appendCepLog('WARN', arguments);
        if (__consoleWarn) {
          __consoleWarn.apply(null, arguments);
        }
      };
      __console.info = function() {
        appendCepLog('INFO', arguments);
        if (__consoleInfo) {
          __consoleInfo.apply(null, arguments);
        }
      };
      __console.debug = function() {
        appendCepLog('DEBUG', arguments);
        if (__consoleDebug) {
          __consoleDebug.apply(null, arguments);
        }
      };
      __console.error = function() {
        appendCepLog('ERROR', arguments);
        if (__consoleError) {
          __consoleError.apply(null, arguments);
        }
      };
    }

    // Initialize log from loglevel.min.js, with fallback
    var log = window.log || {
      warn: function(msg) { if (typeof console !== 'undefined' && console.warn) console.warn(msg); },
      debug: function(msg) { if (typeof console !== 'undefined' && console.debug) console.debug(msg); },
      info: function(msg) { if (typeof console !== 'undefined' && console.info) console.info(msg); },
      error: function(msg) { if (typeof console !== 'undefined' && console.error) console.error(msg); }
    };

    var logReturn = function(result){ log.warn('Result: ' + result);};
    var csInterface = null;

    function safeAlert(message) {
        try {
        if (typeof console !== 'undefined' && console.warn) {
                console.warn(message);
            }
        } catch (e) {
            try {
                if (typeof console !== 'undefined' && console.warn) {
                    console.warn('alert failed: ' + e);
                }
            } catch (_) {}
        }
    }

    function startupClient() {
        if (typeof CSInterface === 'undefined') {
            safeAlert('Animate client startup error: CSInterface is undefined');
            return;
        }
        if (typeof SystemPath === 'undefined') {
            safeAlert('Animate client startup error: SystemPath is undefined');
            return;
        }
        appendCepLog('INFO', ['Animate CEP client starting up.']);
        csInterface = new CSInterface();
        appendCepLog('INFO', ['CSInterface initialized.']);
        var extensionRoot = csInterface.getSystemPath(SystemPath.EXTENSION);
        extensionRoot = extensionRoot.replace(/\\/g, '/');
        appendCepLog('INFO', ['Animate CEP client starting at extension root: ' + extensionRoot]);

        log.warn("script start");

        WSRPC.DEBUG = true;
        WSRPC.TRACE = true;

    function loadHostScript() {
      var hostScriptPath = extensionRoot + '/host/index.js';
      appendCepLog('INFO', ['Loading host script from:', hostScriptPath]);
      return new Promise(function(resolve, reject) {
        if (!window.cep || !window.cep.fs) {
          reject(new Error('CEP filesystem API is unavailable'));
          return;
        }

        var fileResult = window.cep.fs.readFile(hostScriptPath);
        if (!fileResult || fileResult.err !== 0 || typeof fileResult.data !== 'string') {
          reject(new Error('Failed to read host/index.js (err=' + (fileResult && fileResult.err) + ')'));
          return;
        }

        // Evaluate the host script contents once in Animate's host scripting context.
        // This registers all functions (fileOpen, saveWorkfile, etc.) as globals in
        // the host scope, so later csInterface.evalScript("fileOpen(...)") calls work.
        csInterface.evalScript(fileResult.data, function(result) {
          if (result === 'EvalScript error.') {
            appendCepLog('ERROR', ['Host script eval failed']);
            reject(new Error('Failed to evaluate host/index.js'));
            return;
          }
          appendCepLog('INFO', ['Host script loaded successfully']);
          resolve(result);
        });
      });
    }

    // Animate CEP can intermittently fail when evalScript calls overlap.
    // Keep a single queue so every eval runs strictly in sequence.
    var __evalQueue = Promise.resolve();

    function runEvalScript(script) {
        function executeEval() {
        var scriptText = String(script || '');
        appendCepLog('DEBUG', ['runEvalScript begin', 'len=' + scriptText.length, 'script=' + scriptText]);
        return new Promise(function(resolve){
          csInterface.evalScript(scriptText, function(result) {
            appendCepLog('DEBUG', ['runEvalScript end', 'result=' + String(result)]);
            resolve(result);
          });
            });
        }

        var queued = __evalQueue.then(executeEval, executeEval);
        __evalQueue = queued.then(function(){
            return null;
        }, function(){
            return null;
        });
        return queued;
    }
    
    function verifyHostApiSurface() {
      return runEvalScript("(function(){return [typeof fileOpen,typeof saveWorkfile,typeof getHeadline].join('|');})()")
        .then(function(result){
          log.warn('Host API probe after load: ' + String(result));
          return result;
        });
    }

    /** main entry point **/
    log.warn("Client script loading");
    log.warn("WSRPC debugging enabled");

    // get websocket server url from environment value

    function getWebsocketUrlFromNodeEnv() {
      try {
        if (typeof process !== "undefined" && process && process.env) {
          return process.env.WEBSOCKET_URL || "";
        }
      } catch (err) {
        log.warn("Node env lookup failed:", err);
      }
      return "";
    }

    async function startUp(url) {
      log.warn("startUp() using Node env lookup");
      var res = getWebsocketUrlFromNodeEnv();

      if (!res) {
        log.warn("process.env.WEBSOCKET_URL missing, using fallback");
        res = "ws://localhost:8098/ws/";
      }

      return verifyHostApiSurface().then(function() {
        main(res);
      });
    }


    function get_extension_version(){
        /** Returns version number from extension manifest.xml **/
        // log.debug("get_extension_version")
        var path = csInterface.getSystemPath(SystemPath.EXTENSION);
        // log.debug("extension path " + path);

        var result = window.cep.fs.readFile(path + "/CSXS/manifest.xml");
        var version = undefined;
        if(result.err === 0){
            if (window.DOMParser) {
                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(result.data.toString(), 'text/xml');
                const children = xmlDoc.children;

                for (let i = 0; i <= children.length; i++) {
                    if (children[i] && children[i].getAttribute('ExtensionBundleVersion')) {
                        version = children[i].getAttribute('ExtensionBundleVersion');
                    }
                }
            }
        }
        return version
    }

    function main(websocket_url){
      // creates connection to 'websocket_url', registers routes
      log.warn("websocket_url", websocket_url);
      var default_url = 'ws://localhost:8099/ws/';

      if  (websocket_url == ''){
           websocket_url = default_url;
      }
      log.warn("connecting to:", websocket_url);
      RPC = new WSRPC(websocket_url, 5000); // spin connection

      // Add connection event handlers
      RPC.onConnect = function() {
        log.warn("RPC connection established successfully");
      };
      
      RPC.onDisconnect = function() {
        log.warn("RPC connection disconnected");
      };
      
      RPC.onError = function(error) {
        log.warn("RPC connection error:", error);
      };

      RPC.connect();

      log.warn("RPC.connect() called");

      function EscapeStringForJSX(str){
      // Replaces:
      //  \ with \\
      //  ' with \'
      //  " with \"
      // See: https://stackoverflow.com/a/3967927/5285364
          return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
      }
      
      

      RPC.addRoute('Animate.open', function (data) {
        appendCepLog('INFO', ['Animate.open route invoked', 'payload=' + JSON.stringify(data || {})]);
        var openPath = String((data && data.path) || '');
        appendCepLog('INFO', ['Animate.open route begin path:', openPath]);
        var encodedPath = JSON.stringify(openPath);
        return runEvalScript("fileOpen(" + encodedPath + ")")
          .then(function(result){
            appendCepLog('INFO', ['Animate.open route end result:', String(result)]);
            return result;
          }, function(error) {
            appendCepLog('ERROR', ['Animate.open route failed:', String(error)]);
            throw error;
          });
      });



      RPC.addRoute('Animate.host_trace', function (data) {
            var encodedMessage = JSON.stringify(String((data && data.message) || ''));
            var traceScript = "(function(){try{var m=" + encodedMessage + ";if(typeof host_trace==='function'){host_trace(m);return true;}if(typeof fl!=='undefined'&&typeof fl.trace==='function'){fl.trace('host_trace: '+m);return true;}return false;}catch(e){return false;}})()";
            return runEvalScript(traceScript, {
                label: 'Animate.host_trace',
                retryOnEvalError: false,
                fallback: false
              })
                .then(function(result){
                    return result;
                });
      });

      RPC.addRoute('Animate.read', function (data) {
        appendCepLog('INFO', ['Animate.read route invoked', 'payload=' + JSON.stringify(data || {})]);
        return runEvalScript("getHeadline()")
                  .then(function(result){
                    //   log.warn("getHeadline: " + result);
                      return result;
                  });
      });

      // RPC.addRoute('Animate.get_layers', function (data) {
      //       //   log.warn('Server called client route "get_layers":', data);
      //         return runEvalScript("getLayers()")
      //             .then(function(result){
      //               //   log.warn("getLayers: " + result);
      //                 return result;
      //             });
      // });
      RPC.addRoute('Animate.get_color_profile_name', function (data) {
            //   log.warn('Server called client route "get_color_profile_name":', data);
              return runEvalScript("getColorProfileName()")
                .then(function (result) {
                //   log.warn("get_color_profile_name: " + result);
                  return result;
                });
      });

      RPC.addRoute('Animate.get_document_settings', function (data) {
            //   log.warn('Server called client route "get_document_settings":', data);
              return runEvalScript("getDocumentSettings()")
                .then(function (result) {
                //   log.warn("get_document_settings: " + result);
                  return result;
                });
      });
      RPC.addRoute('Animate.set_document_settings', function (data) {
            //   log.warn('Server called client route "set_document_settings":', data);
              var resolution = data.resolution !== undefined ? data.resolution : null;
              var mode = data.mode !== undefined ? "'" + data.mode + "'" : null;
              var bits = data.bits !== undefined ? "'" + data.bits + "'" : null;
              return runEvalScript("setDocumentSettings(" + resolution + ", " +
                                   mode + ", " + bits + ")")
                .then(function (result) {
                //   log.warn("set_document_settings: " + result);
                  return result;
                });
      });

      RPC.addRoute('Animate.set_visible', function (data) {
            //   log.warn('Server called client route "set_visible":', data);
              return runEvalScript("setVisible(" + data.layer_id + ", " +
                                   data.visibility + ")")
                  .then(function(result){
                    //   log.warn("setVisible: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.set_layers_visibility', function (data) {
            //   log.warn('Server called client route "set_layers_visibility":', data);
              return runEvalScript("setLayersVisibility('" + data.visibility_map + "')")
                  .then(function(result){
                    //   log.warn("setLayersVisibility: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.get_active_document_name', function (data) {
        //   log.warn('Server called client route "get_active_document_name":',
            // data);
          return runEvalScript("getActiveDocumentName()")
                  .then(function(result){
                    //   log.warn("save: " + result);
                      return result;
                  });
      });
      RPC.addRoute('Animate.export_png_sequence', function (data) {
        return runEvalScript("(function(){var path=" + JSON.stringify(String(data.path || '')) + ";try{var p=String(path||'');if(!p){return false;}p=p.split('\\\\').join('/');if(typeof exportPngSequence==='function'){return !!exportPngSequence(p);}return false;}catch(e){return false;}})()", {
          label: 'Animate.export_png_sequence',
          retryOnEvalError: false,
          fallback: ''
        }).then(function(result){
          //   log.warn("export_png_sequence: " + result);
            return result;
        });
      });

      RPC.addRoute('Animate.export_movie', function (data) {
        var encodedPath = JSON.stringify(String((data && data.path) || ''));
        var includeAlpha = JSON.stringify(String((data && data.include_alpha) || ''));
        return runEvalScript("exportMovie(" + encodedPath + "," + includeAlpha + ")")
      })

      RPC.addRoute('Animate.export_swf', function (data) {
        var encodedPath = JSON.stringify(String((data && data.path) || ''));
        return runEvalScript("exportSwf(" + encodedPath + ")")
      })


      RPC.addRoute('Animate.get_active_document_full_name', function (data) {
            //   log.warn('Server called client route ' +
                    //    '"get_active_document_full_name":', data);
          appendCepLog('INFO', ['Animate.get_active_document_full_name route invoked']);      
          return runEvalScript("getActiveDocumentFullName()")
                  .then(function(result){
                    //   log.warn("save: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.save', function (data) {
            //   log.warn('Server called client route "save":', data);

          return runEvalScript("save()")
                  .then(function(result){
                    //   log.warn("save: " + result);
                      return result;
                  });
      });

              RPC.addRoute('Animate.save_workfile', function (data) {
                var encodedPath = JSON.stringify(String((data && data.path) || ''));
                return runEvalScript("saveWorkfile(" + encodedPath + ")")
                  .then(function(result){
                    return result;
                  });
              });

              RPC.addRoute('Animate.save_copy', function (data) {
                var encodedPath = JSON.stringify(String((data && data.path) || ''));
                return runEvalScript("saveCopy(" + encodedPath + ")", {
                    label: 'Animate.save_copy',
                    retryOnEvalError: false,
                    fallback: false
                  })
                    .then(function(result){
                      return result;
                    });
              });

      RPC.addRoute('Animate.get_selected_layers', function (data) {
            //   log.warn('Server called client route "get_selected_layers":', data);

              return runEvalScript("getSelectedLayers()")
                  .then(function(result){
                    //   log.warn("get_selected_layers: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.get_layer_blend_mode', function (data) {
            //   log.warn('Server called client route "get_layer_blend_mode":', data);
              return runEvalScript("getLayerBlendMode(" + data.layer_id + ")")
                  .then(function(result){
                    //   log.warn("get_layer_blend_mode: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.create_group', function (data) {
            //   log.warn('Server called client route "create_group":', data);

              return runEvalScript("createGroup('" + data.name + "')")
                  .then(function(result){
                    //   log.warn("createGroup: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.group_selected_layers', function (data) {
            //   log.warn('Server called client route "group_selected_layers":',
                    //    data);

              return runEvalScript("groupSelectedLayers(null, "+
                                   "'" + data.name +"')")
                  .then(function(result){
                    //   log.warn("group_selected_layers: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.merge_all_layersets', function (data) {
            // log.warn('Server called client route "merge_all_layersets":',
                    // data);

            return runEvalScript("mergeAllLayerSets('" + data.parent_set + "')")
                .then(function(result){
                    // log.warn("merge_all_layersets: " + result);
                    return result;
                });
      });

      RPC.addRoute('Animate.dissolve_layerset', function (data) {
            // log.warn('Server called client route "dissolve_layerset":',
                    // data);

            return runEvalScript("dissolveLayerSet('" + data.layerset_id + "')")
                .then(function(result){
                    // log.warn("dissolve_layerset: " + result);
                    return result;
                });
      });

      RPC.addRoute('Animate.import_smart_object', function (data) {
            //   log.warn('Server called client "import_smart_object":', data);
              var escapedPath = EscapeStringForJSX(data.path);
              return runEvalScript("importSmartObject('" + escapedPath +"', " +
                                                      "'"+ data.name +"',"+
                                                      + data.as_reference +")")
                  .then(function(result){
                    //   log.warn("import_smart_object: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.replace_smart_object', function (data) {
            //   log.warn('Server called route "replace_smart_object":', data);
              var escapedPath = EscapeStringForJSX(data.path);
              return runEvalScript("replaceSmartObjects("+data.layer_id+"," +
                                                        "'" + escapedPath +"',"+
                                                        "'"+ data.name +"')")
                  .then(function(result){
                    //   log.warn("replaceSmartObjects: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.delete_layer', function (data) {
            //   log.warn('Server called route "delete_layer":', data);
              return runEvalScript("deleteLayer("+data.layer_id+")")
                  .then(function(result){
                    //   log.warn("delete_layer: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.rename_layer', function (data) {
        // log.warn('Server called route "rename_layer":', data);
        return runEvalScript("renameLayer("+data.layer_id+", " +
                                          "'"+ data.name +"')")
            .then(function(result){
                // log.warn("rename_layer: " + result);
                return result;
            });
});

      RPC.addRoute('Animate.select_layers', function (data) {
            //   log.warn('Server called client route "select_layers":', data);

              return runEvalScript("selectLayers('" + data.layers +"')")
                  .then(function(result){
                    //   log.warn("select_layers: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.is_saved', function (data) {
        //   log.warn('Server called client route "is_saved":', data);

          return runEvalScript("isSaved()")
                  .then(function(result){
                      log.warn("is_saved: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.saveAs', function (data) {
            //   log.warn('Server called client route "saveAsJPEG":', data);
              var encodedImagePath = JSON.stringify(String((data && data.image_path) || ''));
              var encodedExt = JSON.stringify(String((data && data.ext) || ''));
              var encodedAsCopy = (data && data.as_copy) ? 'true' : 'false';
              var saveAsScript = "saveAs(" + encodedImagePath + "," + encodedExt + "," + encodedAsCopy + ")";
              return runEvalScript(saveAsScript, {
                    label: 'Animate.saveAs',
                    retryOnEvalError: false,
                    fallback: false
                })
                  .then(function(result){
                    //   log.warn("save: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.duplicate_document', function (data) {
            //   log.warn('Server called client route "duplicate_document":', data);
              return runEvalScript("duplicateDocument('" + data.newName + "')")
                  .then(function(result){
                      log.warn("duplicated: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.close_document', function (data) {
                // log.warn('Server called client route "close_document":', data);
            var encodedId = JSON.stringify(data && data.id !== undefined ? data.id : null);
            return runEvalScript("(function(){var id="+encodedId+";try{if(typeof fl==='undefined'||!fl.getDocumentDOM){return false;}if(typeof closeDocument==='function'){var res=closeDocument(id);if(res!==undefined&&res!==null){return !!res;}}var doc=fl.getDocumentDOM();if(!doc||typeof doc.close!=='function'){return false;}try{doc.close(false);}catch(e1){doc.close();}return true;}catch(e){return false;}})()", {
                label: 'Animate.close_document',
                retryOnEvalError: false,
                fallback: false
              })
                    .then(function(result){
                        // log.warn("closed: " + result);
                        return result;
                    });
      });

      RPC.addRoute('Animate.revert_to_previous', function (data) {
            // log.warn('Server called client route "revertToPrevious":', data);
          return runEvalScript("(function(){try{if(typeof fl==='undefined'||!fl.getDocumentDOM){return false;}if(typeof revertToPrevious==='function'){var res=revertToPrevious();if(res!==undefined&&res!==null){return !!res;}}var doc=fl.getDocumentDOM();if(!doc){return false;}if(typeof doc.canRevert==='function'&& !doc.canRevert()){return true;}if(typeof doc.revert==='function'){doc.revert();return true;}return false;}catch(e){return false;}})()", {
              label: 'Animate.revert_to_previous',
              retryOnEvalError: false,
              fallback: false
            })
                .then(function(result){
                    // log.warn("reverted: " + result);
                    return result;
                });
      });

      RPC.addRoute('Animate.imprint', function (data) {
            //   log.warn('Server called client route "imprint":', data);
              var escaped = data.payload.replace(/\n/g, "\\n");
              return runEvalScript("imprint('" + escaped + "')")
                  .then(function(result){
                    //   log.warn("imprint: " + result);
                      return result;
                  });
      });

      RPC.addRoute('Animate.get_extension_version', function (data) {
        // log.warn('Server called client route "get_extension_version":', data);
        return get_extension_version();
      });

      RPC.addRoute('Animate.close', function (data) {
        // log.warn('Server called client route "close":', data);
        return runEvalScript("(function(){try{if(typeof fl==='undefined'||!fl.getDocumentDOM){return false;}if(typeof close==='function'){var res=close();if(res!==undefined&&res!==null){return !!res;}}var doc=fl.getDocumentDOM();if(!doc||typeof doc.close!=='function'){return false;}try{doc.close(false);}catch(e1){doc.close();}return true;}catch(e){return false;}})()", {
          label: 'Animate.close',
          retryOnEvalError: false,
          fallback: false
        });
      });

      RPC.addRoute('Animate.eval_code', function (data) {
        // log.warn('Server called client route "eval_code":', data);
        return runEvalScript(data.code).then(function(result){
                      return result;
                  });
      });

      RPC.call('Animate.ping').then(function (data) {
        //   log.warn('Result for calling server route "ping": ', data);
          log.warn('Animate.ping RPC handshake OK');
          return true;

      }, function (error) {
        log.warn("ERROR: RPC.call('Animate.ping') failed:", error);
      });

    }

    loadHostScript()
      .then(function() {
        return startUp('WEBSOCKET_URL');
      })
      .catch(function(error) {
        log.error('Animate host initialization failed:', error);
      });
  }

    try {
      startupClient();
    } catch (e) {
        safeAlert('Animate client startup exception:\n' + e);
        if (typeof console !== 'undefined' && console.error) {
            console.error(e);
        }
    }

    // log.warn("end script");
