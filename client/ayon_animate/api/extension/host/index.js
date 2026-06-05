host_trace = function(message) {
    try {
        fl.trace("host_trace: " + message);
    } catch (_) {
        // Never throw from logger path.
        debugAlert("host_trace: failed trace" );
    }
}

debugAlert = function(message) {
    fl.trace(message);
}

fileOpen = function(path) {
    try {
        fl.trace('fileOpen: begin path=' + String(path || ''));
        if (typeof fl === 'undefined' || !fl.openDocument) {
            fl.trace('fileOpen: end unavailable');
            return false;
        }

        // fl.openDocument requires a file URI (file:///C:/path/file.fla).
        // Convert plain platform path to file URI if not already one.
        var p = String(path || '').replace(/\\/g, '/');
        if (!p) { return false; }
        var uri = (p.indexOf('file://') === 0)
            ? p
            : ('file:///' + (p.charAt(0) === '/' ? p.slice(1) : p));

        try {
            fl.openDocument(uri);
            fl.trace('fileOpen: end success uri=' + uri);
            return true;
        } catch (e1) {
            // Fallback: try the raw path as-is.
            fl.openDocument(p);
            fl.trace('fileOpen: end success raw path=' + p);
            return true;
        }
    } catch (e) {
        try {
            fl.trace('fileOpen: end failure ' + e);
        } catch (_) {}
        return false;
    }
}

_normalizeAnimatePath = function(path) {
    return String(path || '').replace(/\\/g, '/');
}

_toAnimateUri = function(path) {
    var p = _normalizeAnimatePath(path);
    if (!p) {
        return '';
    }
    if (p.indexOf('file://') === 0) {
        return p;
    }
    return 'file:///' + (p.charAt(0) === '/' ? p.slice(1) : p);
}

save = function() {
    try {
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            fl.trace('save: fl.getDocumentDOM unavailable');
            return false;
        }

        var doc = fl.getDocumentDOM();
        if (!doc) {
            fl.trace('save: no active document');
            return false;
        }

        if (typeof doc.save === 'function') {
            doc.save();
        } else {
            fl.trace('save: no supported save method available');
            return false;
        }

        fl.trace('save: success');
        return true;
    } catch (e) {
        fl.trace('save failed: ' + e);
        return false;
    }
}

saveWorkfile = function(imagePath) {
    try {
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            fl.trace('saveWorkfile: fl.getDocumentDOM unavailable');
            return false;
        }

        var doc = fl.getDocumentDOM();
        if (!doc) {
            fl.trace('saveWorkfile: no active document');
            return false;
        }

        var p = _normalizeAnimatePath(imagePath);
        if (!p) {
            fl.trace('saveWorkfile: empty imagePath');
            return false;
        }

        var currentPath = _normalizeAnimatePath(doc.path || doc.pathURI || '');
        fl.trace('saveWorkfile currentPath: ' + currentPath);
        fl.trace('saveWorkfile targetPath: ' + p);
        if (currentPath && currentPath === p) {
            fl.trace('saveWorkfile: target equals current path, delegating to save()');
            return save();
        }

        if (typeof doc.saveAsCopy !== 'function') {
            fl.trace('saveWorkfile: doc.saveAsCopy unavailable');
            return false;
        }

        var uri = _toAnimateUri(p);

        fl.trace('saveWorkfile uri: ' + uri);
        fl.trace('saveWorkfile: starting saveAsCopy');
        try {
            doc.saveAsCopy(uri, false);
            fl.trace('saveWorkfile: saveAsCopy(uri) succeeded');
        } catch (uriErr) {
            fl.trace('saveWorkfile URI failed, trying raw path: ' + uriErr);
            doc.saveAsCopy(p, false);
            fl.trace('saveWorkfile: saveAsCopy(raw path) succeeded');
        }

        if (typeof doc.close !== 'function') {
            fl.trace('saveWorkfile: doc.close unavailable');
            return false;
        }

        fl.trace('saveWorkfile: closing original document');
        try {
            doc.close(false);
            fl.trace('saveWorkfile: close(false) succeeded');
        } catch (closeErr) {
            fl.trace('saveWorkfile close(false) failed, trying close(): ' + closeErr);
            doc.close();
            fl.trace('saveWorkfile: close() succeeded');
        }

        fl.trace('saveWorkfile: reopening saved workfile');
        var reopened = fileOpen(uri);
        fl.trace('saveWorkfile: reopen via uri result=' + reopened);
        if (!reopened) {
            reopened = fileOpen(p);
            fl.trace('saveWorkfile: reopen via raw path result=' + reopened);
        }
        return reopened;
    } catch (e) {
        fl.trace('saveWorkfile failed: ' + e);
        return false;
    }
}

saveCopy = function(imagePath) {
    try {
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            fl.trace('saveCopy: fl.getDocumentDOM unavailable');
            return false;
        }

        var doc = fl.getDocumentDOM();
        if (!doc) {
            fl.trace('saveCopy: no active document');
            return false;
        }

        if (typeof doc.saveAsCopy !== 'function') {
            fl.trace('saveCopy: doc.saveAsCopy unavailable');
            return false;
        }

        var p = _normalizeAnimatePath(imagePath);
        if (!p) {
            fl.trace('saveCopy: empty imagePath');
            return false;
        }

        var uri = _toAnimateUri(p);

        fl.trace('saveCopy: ' + p);
        try {
            doc.saveAsCopy(uri, false);
            return true;
        } catch (uriErr) {
            doc.saveAsCopy(p, false);
            return true;
        }
    } catch (e) {
        fl.trace('saveCopy failed: ' + e);
        return false;
    }
}

saveAs = function(imagePath, ext, asCopy) {
    fl.trace('saveAs compatibility wrapper ext=' + ext + ' asCopy=' + asCopy);
    if (asCopy) {
        return saveCopy(imagePath);
    }
    return saveWorkfile(imagePath);
}

isSaved = function() {
    try {
        fl.trace('isSaved: begin');
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            fl.trace('isSaved: fl.getDocumentDOM unavailable');
            fl.trace('isSaved: end false (no fl/getDocumentDOM)');
            return false;
        }

        fl.trace('isSaved: calling fl.getDocumentDOM()');
        var doc = fl.getDocumentDOM();
        fl.trace('isSaved: doc=' + (doc ? 'found' : 'missing'));
        if (!doc) {
            fl.trace('isSaved: no active document');
            fl.trace('isSaved: end false (no doc)');
            return false;
        }

        // Animate JSAPI documents path/pathURI and canRevert(), not doc.saved.
        var docPath = null;
        var docPathUri = null;

        try {
            fl.trace('isSaved: reading doc.path');
            docPath = doc.path;
            fl.trace('isSaved: doc.path=' + String(docPath));
        } catch (pathErr) {
            fl.trace('isSaved: doc.path read failed: ' + pathErr);
        }

        try {
            fl.trace('isSaved: reading doc.pathURI');
            docPathUri = doc.pathURI;
            fl.trace('isSaved: doc.pathURI=' + String(docPathUri));
        } catch (pathUriErr) {
            fl.trace('isSaved: doc.pathURI read failed: ' + pathUriErr);
        }

        var hasPath = !!(docPath || docPathUri);
        fl.trace('isSaved: hasPath=' + hasPath);
        if (!hasPath) {
            fl.trace('isSaved: document has no path yet (never saved)');
            fl.trace('isSaved: end false (unsaved new doc)');
            return false;
        }

        fl.trace('isSaved: typeof doc.canRevert=' + typeof doc.canRevert);
        if (typeof doc.canRevert === 'function') {
            var canRevert = null;
            try {
                fl.trace('isSaved: calling doc.canRevert()');
                canRevert = doc.canRevert();
                fl.trace('isSaved: doc.canRevert()=' + String(canRevert));
            } catch (canRevertErr) {
                fl.trace('isSaved: doc.canRevert() failed: ' + canRevertErr);
                fl.trace('isSaved: end false (canRevert failure)');
                return false;
            }

            // If document can revert, there are unsaved changes.
            var savedState = !canRevert;
            fl.trace('isSaved via canRevert: ' + savedState);
            fl.trace('isSaved: end ' + savedState + ' (via canRevert)');
            return savedState;
        }

        // If canRevert is unavailable, treat a path-bearing document as saved.
        fl.trace('isSaved: fallback true (path exists, no canRevert)');
        fl.trace('isSaved: end true (fallback)');
        return true;
    } catch (e) {
        fl.trace('isSaved failed: ' + e);
        try {
            fl.trace('isSaved: end false (exception)');
        } catch (_) {}
        return false;
    }
}

getActiveDocumentFullName = function() {
    try {
        fl.trace('getActiveDocumentFullName: begin');
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            fl.trace('getActiveDocumentFullName: fl.getDocumentDOM unavailable');
            fl.trace('getActiveDocumentFullName: end unavailable');
            return null;
        }

        var doc = fl.getDocumentDOM();
        fl.trace('getActiveDocumentFullName: doc=' + (doc ? 'found' : 'missing'));
        if (!doc) {
            fl.trace('getActiveDocumentFullName: no active document');
            fl.trace('getActiveDocumentFullName: end no document');
            return null;
        }

        var fullName = null;

        try {
            fl.trace('getActiveDocumentFullName: reading doc.path');
            fullName = doc.path;
            fl.trace('getActiveDocumentFullName: doc.path value=' + String(fullName));
        } catch (pathErr) {
            fl.trace('getActiveDocumentFullName: doc.path failed: ' + pathErr);
            try {
                fl.trace('getActiveDocumentFullName: doc.path failed ' + pathErr);
            } catch (_) {}
        }

        if (!fullName) {
            try {
                fl.trace('getActiveDocumentFullName: reading doc.pathURI');
                fullName = doc.pathURI;
                fl.trace('getActiveDocumentFullName: doc.pathURI value=' + String(fullName));
            } catch (pathUriErr) {
                fl.trace('getActiveDocumentFullName: doc.pathURI failed: ' + pathUriErr);
                try {
                    fl.trace('getActiveDocumentFullName: doc.pathURI failed ' + pathUriErr);
                } catch (_) {}
            }
        }

        if (!fullName) {
            try {
                fl.trace('getActiveDocumentFullName: reading doc.fullName');
                fullName = doc.fullName;
                fl.trace('getActiveDocumentFullName: doc.fullName value=' + String(fullName));
            } catch (fullNameErr) {
                fl.trace('getActiveDocumentFullName: doc.fullName failed: ' + fullNameErr);
                try {
                    fl.trace('getActiveDocumentFullName: doc.fullName failed ' + fullNameErr);
                } catch (_) {}
            }
        }

        if (!fullName) {
            fl.trace('getActiveDocumentFullName: no saved path available');
            fl.trace('getActiveDocumentFullName: end no path');
            return null;
        }

        // evalScript return transport can break on raw Windows backslashes.
        // Normalize to forward slashes before returning to panel context.
        var safeFullName = String(fullName).replace(/\\/g, '/');
        fl.trace('getActiveDocumentFullName: end path=' + safeFullName);
        return safeFullName;
    } catch (e) {
        try {
            fl.trace('getActiveDocumentFullName: end failure ' + e);
        } catch (_) {}
        return null;
    }
}

getActiveDocumentName = function() {
    try {
        var fullPath = getActiveDocumentFullName();
        if (!fullPath) {
            return null;
        }

        var normalizedPath = String(fullPath).replace(/\\/g, '/');
        var pathParts = normalizedPath.split('/');
        var name = pathParts[pathParts.length - 1] || null;

        fl.trace('getActiveDocumentName: ' + name);
        return name;
    } catch (e) {
        fl.trace('getActiveDocumentName failed: ' + e);
        return null;
    }
}

getHeadline = function() {
    // Metadata is stored in doc.description rather than XMP getMetadata() which can crash on empty docs.
    try {
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            fl.trace('getHeadline: fl.getDocumentDOM unavailable');
            return '';
        }

        var doc = fl.getDocumentDOM();
        if (!doc) {
            fl.trace('getHeadline: no active document');
            return '';
        }

        var headline = doc.description || '';
        fl.trace('getHeadline: ' + headline);
        return headline;
    } catch (e) {
        fl.trace('getHeadline failed: ' + e);
        return '';
    }
}

imprint = function(payload) {
    // Store AYON instance/container metadata as a JSON string in doc.description
    var doc = fl.getDocumentDOM();
    doc.description = String(payload || '');
    fl.trace("imprinted metadata: " + doc.description);

    return true;
}
getImprint = function() {
    var doc = fl.getDocumentDOM();
    var imprintData = doc.description || '';
    return imprintData;
}

testMetadataAndImprint = function() {
    var doc = fl.getDocumentDOM();

    fl.trace("initial description: " + doc.description);
    var testData = {
        timestamp: String(new Date()),
        random: Math.random()
    };
    doc.description = String(testData);

    fl.trace("stored description: ");
    for (var k in testData) {
    fl.trace(k + ": " + testData[k]);
};
}

setPublishSettings = function(opts) {
    // @TODO - eventually will take opts from Ayon settings UI, for now hardcoded in getPublishSettings().
    
    var doc = fl.getDocumentDOM();
    var profile = doc.exportPublishProfileString();
    //fl.trace("Current publish profile: " + profile);
    var newProfile = setPngPublishSettings(profile, opts.png);
    newProfile = setSwfPublishSettings(newProfile, opts.swf);
    fl.trace("New publish profile: " + newProfile);
    doc.importPublishProfileString(newProfile);
}

getPublishSettings = function() {
    // OVERRIDE - eventually will collect settings from Ayon settings UI. 
    var pngOpts = {
        width: 1920,
        height: 1080,
        matchMovieDim: "1",
        smooth: "1",
        bitDepth: "24-bit with Alpha",
        maxColors: "255"
    };
    var swfOpts = {
        topDown: '',
        fireFox: '',
        report: 0,
        protect: 0,
        optimizeForAE: 1,
        omitTraceActions: 0,
        quality: 100,
        deblockingFilter: 0,
        streamFormat: 3,
        streamCompress: 17,
        eventFormat: 3,
        eventCompress: 17,
        overrideSounds: 0,
        version: 43,
        externalPlayer: 'FlashPlayer32.0',
        actionScriptVersion: 3,
        packageExportFrame: 1,
        packagePaths: '',
        as3PackagePaths: '.',
        as3ConfigConst: 'CONFIG::FLASH_AUTHORING="true";',
        debuggingPermitted: 0,
        debuggingPassword: '',
        compressMovie: 0,
        compressionType: 0,
        invisibleLayer: 0,
        deviceSound: 0,
        streamUse8kSampleRate: 0,
        eventUse8kSampleRate: 0,
        useNetwork: 0,
        documentClass: '',
        as3Strict: 2,
        as3Coach: 4,
        as3AutoDeclare: 4096,
        as3Dialect: 'AS3',
        as3ExportFrame: 1,
        as3Optimize: 1,
        exportSwc: 0,
        scriptStuckDelay: 15,
        includeXMP: 1,
        hardwareAcceleration: 0
    }
    return {
        png: pngOpts,
        swf: swfOpts
    };
}

setSwfPublishSettings = function(profile, opts) {
    var doc = fl.getDocumentDOM();
    try {
        var newProfile = replacePublishSwfProperties(profile, opts);
        return newProfile;
    } catch (e) {
        return false;
    }
}
replacePublishSwfProperties = function(profileXml, opts) {
    var doc = fl.getDocumentDOM();

    var topDown = String(opts.topDown);
    var fireFox = String(opts.fireFox);
    var report = String(opts.report);
    var protect = String(opts.protect);
    var optimizeForAE = String(opts.optimizeForAE);
    var omitTraceActions = String(opts.omitTraceActions);
    var quality = String(opts.quality);
    var deblockingFilter = String(opts.deblockingFilter);
    var streamFormat = String(opts.streamFormat);
    var streamCompress = String(opts.streamCompress);
    var eventFormat = String(opts.eventFormat);
    var eventCompress = String(opts.eventCompress);
    var overrideSounds = String(opts.overrideSounds);
    var version = String(opts.version);
    var externalPlayer = String(opts.externalPlayer);
    var actionScriptVersion = String(opts.actionScriptVersion);
    var packageExportFrame = String(opts.packageExportFrame);
    var packagePaths = String(opts.packagePaths);
    var as3PackagePaths = String(opts.as3PackagePaths);
    var as3ConfigConst = String(opts.as3ConfigConst);
    var debuggingPermitted = String(opts.debuggingPermitted);
    var debuggingPassword = String(opts.debuggingPassword);
    var compressMovie = String(opts.compressMovie);
    var compressionType = String(opts.compressionType);
    var invisibleLayer = String(opts.invisibleLayer);
    var deviceSound = String(opts.deviceSound);
    var streamUse8kSampleRate = String(opts.streamUse8kSampleRate);
    var eventUse8kSampleRate = String(opts.eventUse8kSampleRate);
    var useNetwork = String(opts.useNetwork);
    var documentClass = String(opts.documentClass);
    var as3Strict = String(opts.as3Strict);
    var as3Coach = String(opts.as3Coach);
    var as3AutoDeclare = String(opts.as3AutoDeclare);
    var as3Dialect = String(opts.as3Dialect);
    var as3ExportFrame = String(opts.as3ExportFrame);
    var as3Optimize = String(opts.as3Optimize);
    var exportSwc = String(opts.exportSwc);
    var scriptStuckDelay = String(opts.scriptStuckDelay);
    var includeXMP = String(opts.includeXMP);
    var hardwareAcceleration = String(opts.hardwareAcceleration);

    var newProfile = profileXml;
    var newSwfEnabledBlock = '<flash>1</flash>';
    var newPropertiesBlock = [
        '<PublishFlashProperties enabled="true">',
        '    <TopDown>' + topDown + '</TopDown>',
        '    <FireFox>' + fireFox + '</FireFox>',
        '    <Report>' + report + '</Report>',
        '    <Protect>' + protect + '</Protect>',
        '    <OptimizeForAE>' + optimizeForAE + '</OptimizeForAE>',
        '    <OmitTraceActions>' + omitTraceActions + '</OmitTraceActions>',
        '    <Quality>' + quality + '</Quality>',
        '    <DeblockingFilter>' + deblockingFilter + '</DeblockingFilter>',
        '    <StreamFormat>' + streamFormat + '</StreamFormat>',
        '    <StreamCompress>' + streamCompress + '</StreamCompress>',
        '    <EventFormat>' + eventFormat + '</EventFormat>',
        '    <EventCompress>' + eventCompress + '</EventCompress>',
        '    <OverrideSounds>' + overrideSounds + '</OverrideSounds>',
        '    <Version>' + version + '</Version>',
        '    <ExternalPlayer>' + externalPlayer + '</ExternalPlayer>',
        '    <ActionScriptVersion>' + actionScriptVersion + '</ActionScriptVersion>',
        '    <PackageExportFrame>' + packageExportFrame + '</PackageExportFrame>',
        '    <PackagePaths>' + packagePaths + '</PackagePaths>',
        '    <AS3PackagePaths>' + as3PackagePaths + '</AS3PackagePaths>',
        '    <AS3ConfigConst>' + as3ConfigConst + '</AS3ConfigConst>',
        '    <DebuggingPermitted>' + debuggingPermitted + '</DebuggingPermitted>',
        '    <DebuggingPassword>' + debuggingPassword + '</DebuggingPassword>',
        '    <CompressMovie>' + compressMovie + '</CompressMovie>',
        '    <CompressionType>' + compressionType + '</CompressionType>',
        '    <InvisibleLayer>' + invisibleLayer + '</InvisibleLayer>',
        '    <DeviceSound>' + deviceSound + '</DeviceSound>',
        '    <StreamUse8kSampleRate>' + streamUse8kSampleRate + '</StreamUse8kSampleRate>',
        '    <EventUse8kSampleRate>' + eventUse8kSampleRate + '</EventUse8kSampleRate>',
        '    <UseNetwork>' + useNetwork + '</UseNetwork>',
        '    <DocumentClass>' + documentClass + '</DocumentClass>',
        '    <AS3Strict>' + as3Strict + '</AS3Strict>',
        '    <AS3Coach>' + as3Coach + '</AS3Coach>',
        '    <AS3AutoDeclare>' + as3AutoDeclare + '</AS3AutoDeclare>',
        '    <AS3Dialect>' + as3Dialect + '</AS3Dialect>',
        '    <AS3ExportFrame>' + as3ExportFrame + '</AS3ExportFrame>',
        '    <AS3Optimize>' + as3Optimize + '</AS3Optimize>',
        '    <ExportSwc>' + exportSwc + '</ExportSwc>',
        '    <ScriptStuckDelay>' + scriptStuckDelay + '</ScriptStuckDelay>',
        '    <IncludeXMP>' + includeXMP + '</IncludeXMP>',
        '    <HardwareAcceleration>' + hardwareAcceleration + '</HardwareAcceleration>',
        '    <AS3Flags>4102</AS3Flags>',
        '    <DefaultLibraryLinkage>rsl</DefaultLibraryLinkage>',
        '    <RSLPreloaderMethod>wrap</RSLPreloaderMethod>',
        '    <RSLPreloaderSWF>$(AppConfig)/ActionScript 3.0/rsls/loader_animation.swf</RSLPreloaderSWF>',
        '    <LibraryPath>',
        '      <library-path-entry>',
        '        <swc-path>$(AppConfig)/ActionScript 3.0/libs</swc-path>',
        '        <linkage>merge</linkage>',
        '      </library-path-entry>',
        '    </LibraryPath>',
        '    <LibraryVersions>',
        '    </LibraryVersions>',
        '    <EnableTelemetry>0</EnableTelemetry>',
        '    <TelemetryPassword></TelemetryPassword>',
        '  </PublishFlashProperties>'
    ].join('\n');
    
    var propRe = /<PublishFlashProperties\b[^>]*>[\s\S]*?<\/PublishFlashProperties>/i;
    if (propRe.test(profileXml)) {
        newProfile = profileXml.replace(propRe, newPropertiesBlock);
    }

    var swfRe = /<swf\b[^>]*>[\s\S]*?<\/swf>/i;
    if (swfRe.test(newProfile)) {
        newProfile = newProfile.replace(swfRe, newSwfEnabledBlock);
    }
    return newProfile;
}

setPngPublishSettings = function(profile) {
    var doc = fl.getDocumentDOM();
    try {
        var opts = {
            width: 1920,
            height: 1080,
            matchMovieDim: "1",
            smooth: "1",
            bitDepth: "24-bit with Alpha",
            maxColors: "255"
        };

        var newProfile = replacePublishPngProperties(profile, opts);
        return newProfile;
    } catch (e) {
        return false;
    }
}

replacePublishPngProperties = function(profileXml, opts) {
    var doc = fl.getDocumentDOM();

    var width = String(opts.width);
    var height = String(opts.height);
    var matchMovieDim = String(opts.matchMovieDim);
    var smooth = String(opts.smooth);
    var bitDepth = String(opts.bitDepth);
    var maxColors = String(opts.maxColors);

    var newProfile = profileXml;

    var newPngEnabledBlock = '<png>1</png>';
    var newPropertiesBlock = [
        '<PublishPNGProperties enabled="true">',
        '    <Width>' + width + '</Width>',
        '    <Height>' + height + '</Height>',
        '    <MatchMovieDim>' + matchMovieDim + '</MatchMovieDim>',
        '    <Smooth>' + smooth + '</Smooth>',
        '    <BitDepth>' + bitDepth + '</BitDepth>',
        '    <MaxColors>' + maxColors + '</MaxColors>',
        '  </PublishPNGProperties>'
    ].join('\n');

    var propRe = /<PublishPNGProperties\b[^>]*>[\s\S]*?<\/PublishPNGProperties>/i;
    if (propRe.test(profileXml)) {
        newProfile = profileXml.replace(propRe, newPropertiesBlock);
    }

    var pngRe = /<png\b[^>]*>[\s\S]*?<\/png>/i;
    if (pngRe.test(newProfile)) {
        newProfile = newProfile.replace(pngRe, newPngEnabledBlock);
    }

    return newProfile;
}

exportPngSequence = function(path) {
    fl.trace("exportPngSequence called");
    var doc = fl.getDocumentDOM();

    fl.trace("exportPngSequence doc: " + (doc ? "found" : "not found"));

    try {
        doc.exportPNG("file:///" + path + ".png", true, false);
        fl.trace("exportPngSequence success: " + path);
        return true;
    }
    catch (e) {
        fl.trace("export failed: " + e);
    }

}



// function getSelectedLayers() {
//     try {
//         if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
//             fl.trace('getSelectedLayers: fl.getDocumentDOM unavailable');
//             return [];
//         }

//         var doc = fl.getDocumentDOM();
//         if (!doc) {
//             fl.trace('getSelectedLayers: no active document');
//             return [];
//         }

//         if (typeof doc.getTimeline === 'function') {
//             var timeline = doc.getTimeline();
//             if (timeline && typeof timeline.layers === 'object') {
//                 var selectedLayers = [];
//                 for (var i = 0; i < timeline.layers.length; i++) {
//                     var layer = timeline.layers[i];
//                     if (layer.selected) {
//                         selectedLayers.push(layer.name);
//                     }
//                 }
//                 fl.trace('getSelectedLayers: ' + selectedLayers.length + ' layers selected');
//                 return selectedLayers;
//             }
//         }

//         fl.trace('getSelectedLayers: no timeline or layers found');
//         return [];
//     } catch (e) {
//         fl.trace('getSelectedLayers failed: ' + e);
//         return [];
//     }
// }
