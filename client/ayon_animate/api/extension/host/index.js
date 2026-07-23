host_trace = function(message) {
    // Commented out to avoid annoying console output during normal operation. Uncomment for dev debugging.

    // try {
    //     fl.trace("host_trace: " + message);
    // } catch (_) {
    //     // Never throw from logger path.
    //     debugAlert("host_trace: failed trace" );
    // }
    return
}

debugAlert = function(message) {
    // Commented out to avoid annoying popups during normal operation. Uncomment for dev debugging.
    // fl.trace(message);
    return
}

fileOpen = function(path) {
    try {
        host_trace('fileOpen: begin path=' + String(path || ''));
        if (typeof fl === 'undefined' || !fl.openDocument) {
            host_trace('fileOpen: end unavailable');
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
            host_trace('fileOpen: end success uri=' + uri);
            return true;
        } catch (e1) {
            // Fallback: try the raw path as-is.
            fl.openDocument(p);
            host_trace('fileOpen: end success raw path=' + p);
            return true;
        }
    } catch (e) {
        try {
            host_trace('fileOpen: end failure ' + e);
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
            host_trace('save: fl.getDocumentDOM unavailable');
            return false;
        }

        var doc = fl.getDocumentDOM();
        if (!doc) {
            host_trace('save: no active document');
            return false;
        }

        if (typeof doc.save === 'function') {
            doc.save();
        } else {
            host_trace('save: no supported save method available');
            return false;
        }

        host_trace('save: success');
        return true;
    } catch (e) {
        host_trace('save failed: ' + e);
        return false;
    }
}

saveWorkfile = function(imagePath) {
    try {
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            host_trace('saveWorkfile: fl.getDocumentDOM unavailable');
            return false;
        }

        var doc = fl.getDocumentDOM();
        if (!doc) {
            host_trace('saveWorkfile: no active document');
            return false;
        }

        var p = _normalizeAnimatePath(imagePath);
        if (!p) {
            host_trace('saveWorkfile: empty imagePath');
            return false;
        }

        var currentPath = _normalizeAnimatePath(doc.path || doc.pathURI || '');
        host_trace('saveWorkfile currentPath: ' + currentPath);
        host_trace('saveWorkfile targetPath: ' + p);
        if (currentPath && currentPath === p) {
            host_trace('saveWorkfile: target equals current path, delegating to save()');
            return save();
        }

        if (typeof doc.saveAsCopy !== 'function') {
            host_trace('saveWorkfile: doc.saveAsCopy unavailable');
            return false;
        }

        var uri = _toAnimateUri(p);

        host_trace('saveWorkfile uri: ' + uri);
        host_trace('saveWorkfile: starting saveAsCopy');
        try {
            doc.saveAsCopy(uri, false);
            host_trace('saveWorkfile: saveAsCopy(uri) succeeded');
        } catch (uriErr) {
            host_trace('saveWorkfile URI failed, trying raw path: ' + uriErr);
            doc.saveAsCopy(p, false);
            host_trace('saveWorkfile: saveAsCopy(raw path) succeeded');
        }

        if (typeof doc.close !== 'function') {
            host_trace('saveWorkfile: doc.close unavailable');
            return false;
        }

        host_trace('saveWorkfile: closing original document');
        try {
            doc.close(false);
            host_trace('saveWorkfile: close(false) succeeded');
        } catch (closeErr) {
            host_trace('saveWorkfile close(false) failed, trying close(): ' + closeErr);
            doc.close();
            host_trace('saveWorkfile: close() succeeded');
        }

        host_trace('saveWorkfile: reopening saved workfile');
        var reopened = fileOpen(uri);
        host_trace('saveWorkfile: reopen via uri result=' + reopened);
        if (!reopened) {
            reopened = fileOpen(p);
            host_trace('saveWorkfile: reopen via raw path result=' + reopened);
        }
        return reopened;
    } catch (e) {
        host_trace('saveWorkfile failed: ' + e);
        return false;
    }
}

saveCopy = function(imagePath) {
    try {
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            host_trace('saveCopy: fl.getDocumentDOM unavailable');
            return false;
        }

        var doc = fl.getDocumentDOM();
        if (!doc) {
            host_trace('saveCopy: no active document');
            return false;
        }

        if (typeof doc.saveAsCopy !== 'function') {
            host_trace('saveCopy: doc.saveAsCopy unavailable');
            return false;
        }

        var p = _normalizeAnimatePath(imagePath);
        if (!p) {
            host_trace('saveCopy: empty imagePath');
            return false;
        }

        var uri = _toAnimateUri(p);

        host_trace('saveCopy: ' + p);
        try {
            doc.saveAsCopy(uri, false);
            return true;
        } catch (uriErr) {
            doc.saveAsCopy(p, false);
            return true;
        }
    } catch (e) {
        host_trace('saveCopy failed: ' + e);
        return false;
    }
}

saveAs = function(imagePath, ext, asCopy) {
    host_trace('saveAs compatibility wrapper ext=' + ext + ' asCopy=' + asCopy);
    if (asCopy) {
        return saveCopy(imagePath);
    }
    return saveWorkfile(imagePath);
}

isSaved = function() {
    try {
        host_trace('isSaved: begin');
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            host_trace('isSaved: fl.getDocumentDOM unavailable');
            host_trace('isSaved: end false (no fl/getDocumentDOM)');
            return false;
        }

        host_trace('isSaved: calling fl.getDocumentDOM()');
        var doc = fl.getDocumentDOM();
        host_trace('isSaved: doc=' + (doc ? 'found' : 'missing'));
        if (!doc) {
            host_trace('isSaved: no active document');
            host_trace('isSaved: end false (no doc)');
            return false;
        }

        // Animate JSAPI documents path/pathURI and canRevert(), not doc.saved.
        var docPath = null;
        var docPathUri = null;

        try {
            host_trace('isSaved: reading doc.path');
            docPath = doc.path;
            host_trace('isSaved: doc.path=' + String(docPath));
        } catch (pathErr) {
            host_trace('isSaved: doc.path read failed: ' + pathErr);
        }

        try {
            host_trace('isSaved: reading doc.pathURI');
            docPathUri = doc.pathURI;
            host_trace('isSaved: doc.pathURI=' + String(docPathUri));
        } catch (pathUriErr) {
            host_trace('isSaved: doc.pathURI read failed: ' + pathUriErr);
        }

        var hasPath = !!(docPath || docPathUri);
        host_trace('isSaved: hasPath=' + hasPath);
        if (!hasPath) {
            host_trace('isSaved: document has no path yet (never saved)');
            host_trace('isSaved: end false (unsaved new doc)');
            return false;
        }

        host_trace('isSaved: typeof doc.canRevert=' + typeof doc.canRevert);
        if (typeof doc.canRevert === 'function') {
            var canRevert = null;
            try {
                host_trace('isSaved: calling doc.canRevert()');
                canRevert = doc.canRevert();
                host_trace('isSaved: doc.canRevert()=' + String(canRevert));
            } catch (canRevertErr) {
                host_trace('isSaved: doc.canRevert() failed: ' + canRevertErr);
                host_trace('isSaved: end false (canRevert failure)');
                return false;
            }

            // If document can revert, there are unsaved changes.
            var savedState = !canRevert;
            host_trace('isSaved via canRevert: ' + savedState);
            host_trace('isSaved: end ' + savedState + ' (via canRevert)');
            return savedState;
        }

        // If can Revert is unavailable, treat a path-bearing document as saved.
        host_trace('isSaved: fallback true (path exists, no canRevert)');
        host_trace('isSaved: end true (fallback)');
        return true;
    } catch (e) {
        host_trace('isSaved failed: ' + e);
        try {
            host_trace('isSaved: end false (exception)');
        } catch (_) {}
        return false;
    }
}

getActiveDocumentFullName = function() {
    try {
        host_trace('getActiveDocumentFullName: begin');
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            host_trace('getActiveDocumentFullName: fl.getDocumentDOM unavailable');
            host_trace('getActiveDocumentFullName: end unavailable');
            return null;
        }

        var doc = fl.getDocumentDOM();
        host_trace('getActiveDocumentFullName: doc=' + (doc ? 'found' : 'missing'));
        if (!doc) {
            host_trace('getActiveDocumentFullName: no active document');
            host_trace('getActiveDocumentFullName: end no document');
            return null;
        }

        var fullName = null;

        try {
            host_trace('getActiveDocumentFullName: reading doc.path');
            fullName = doc.path;
            host_trace('getActiveDocumentFullName: doc.path value=' + String(fullName));
        } catch (pathErr) {
            host_trace('getActiveDocumentFullName: doc.path failed: ' + pathErr);
            try {
                host_trace('getActiveDocumentFullName: doc.path failed ' + pathErr);
            } catch (_) {}
        }

        if (!fullName) {
            try {
                host_trace('getActiveDocumentFullName: reading doc.pathURI');
                fullName = doc.pathURI;
                host_trace('getActiveDocumentFullName: doc.pathURI value=' + String(fullName));
            } catch (pathUriErr) {
                host_trace('getActiveDocumentFullName: doc.pathURI failed: ' + pathUriErr);
                try {
                    host_trace('getActiveDocumentFullName: doc.pathURI failed ' + pathUriErr);
                } catch (_) {}
            }
        }

        if (!fullName) {
            try {
                host_trace('getActiveDocumentFullName: reading doc.fullName');
                fullName = doc.fullName;
                host_trace('getActiveDocumentFullName: doc.fullName value=' + String(fullName));
            } catch (fullNameErr) {
                host_trace('getActiveDocumentFullName: doc.fullName failed: ' + fullNameErr);
                try {
                    host_trace('getActiveDocumentFullName: doc.fullName failed ' + fullNameErr);
                } catch (_) {}
            }
        }

        if (!fullName) {
            host_trace('getActiveDocumentFullName: no saved path available');
            host_trace('getActiveDocumentFullName: end no path');
            return null;
        }

        // evalScript return transport can break on raw Windows backslashes.
        // Normalize to forward slashes before returning to panel context.
        var safeFullName = String(fullName).replace(/\\/g, '/');
        host_trace('getActiveDocumentFullName: end path=' + safeFullName);
        return safeFullName;
    } catch (e) {
        try {
            host_trace('getActiveDocumentFullName: end failure ' + e);
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

        host_trace('getActiveDocumentName: ' + name);
        return name;
    } catch (e) {
        host_trace('getActiveDocumentName failed: ' + e);
        return null;
    }
}

getHeadline = function() {
    // Metadata is stored in doc.description rather than XMP getMetadata() which can crash on empty docs.
    try {
        if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
            host_trace('getHeadline: fl.getDocumentDOM unavailable');
            return '';
        }

        var doc = fl.getDocumentDOM();
        if (!doc) {
            host_trace('getHeadline: no active document');
            return '';
        }

        var headline = doc.description || '';
        host_trace('getHeadline: ' + headline);
        return headline;
    } catch (e) {
        host_trace('getHeadline failed: ' + e);
        return '';
    }
}

imprint = function(payload) {
    // Store AYON instance/container metadata as a JSON string in doc.description
    var doc = fl.getDocumentDOM();
    doc.description = String(payload || '');
    host_trace("imprinted metadata: " + doc.description);

    return true;
}
getImprint = function() {
    var doc = fl.getDocumentDOM();
    var imprintData = doc.description || '';
    return imprintData;
}

testMetadataAndImprint = function() {
    var doc = fl.getDocumentDOM();

    host_trace("initial description: " + doc.description);
    var testData = {
        timestamp: String(new Date()),
        random: Math.random()
    };
    doc.description = String(testData);

    host_trace("stored description: ");
    for (var k in testData) {
    host_trace(k + ": " + testData[k]);
};
}

setPublishSettings = function(opts) {
    // @TODO - eventually will take opts from Ayon settings UI, for now hardcoded in getPublishSettings().
    
    var doc = fl.getDocumentDOM();
    var profile = doc.exportPublishProfileString();
    //host_trace("Current publish profile: " + profile);
    var newProfile = setPngPublishSettings(profile, opts.png);
    newProfile = setSwfPublishSettings(newProfile, opts.swf);
    host_trace("New publish profile: " + newProfile);
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
exportSwf = function(path) {
    fl.trace( "exporting to file:///" + path + ".swf" );
    var doc = fl.getDocumentDOM();
    
    if (doc) {
        doc.exportSWF("file:///" + path + ".swf", true, false);
        return true;      
    }
    return false;
}

exportMovie = function(path,includeAlpha) {
    try {
        var doc = fl.getDocumentDOM();
        
        if (doc) {
            var uri = _toAnimateUri(path + ".mov");
            var frame_count = 0;

            try {
                var timeline = doc.getTimeline();
                if (timeline && timeline.frameCount) {
                    frame_count = Number(timeline.frameCount) || 0;
                }
            } catch (timelineErr) {
                host_trace("exportMovie timeline read failed: " + timelineErr);
            }

            if (frame_count > 0) {
                doc.exportVideo(uri, false, includeAlpha, true, frame_count);
            } else {
                doc.exportVideo(uri, false, includeAlpha, true, 0);
            }

            return true;
        }
    } catch (exportErr) {
        host_trace( "exportMovie failed: " + exportErr );
        return false;
    }
}


exportPngSequence = function(path) {
    host_trace("exportPngSequence called");
    var doc = fl.getDocumentDOM();

    host_trace("exportPngSequence doc: " + (doc ? "found" : "not found"));

    try {
        doc.exportPNG("file:///" + path + ".png", true, false);
        host_trace("exportPngSequence success: " + path);
        return true;
    }
    catch (e) {
        host_trace("export failed: " + e);
    }

}



// function getSelectedLayers() {
//     try {
//         if (typeof fl === 'undefined' || !fl.getDocumentDOM) {
//             host_trace('getSelectedLayers: fl.getDocumentDOM unavailable');
//             return [];
//         }

//         var doc = fl.getDocumentDOM();
//         if (!doc) {
//             host_trace('getSelectedLayers: no active document');
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
//                 host_trace('getSelectedLayers: ' + selectedLayers.length + ' layers selected');
//                 return selectedLayers;
//             }
//         }

//         host_trace('getSelectedLayers: no timeline or layers found');
//         return [];
//     } catch (e) {
//         host_trace('getSelectedLayers failed: ' + e);
//         return [];
//     }
// }
