import os
import re
import shutil
import zipfile
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

OFFLINE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Connection Lost</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: radial-gradient(circle at center, #1e1e24 0%, #000000 100%);
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
            text-align: center;
            padding-top: env(safe-area-inset-top, 24px);
            padding-bottom: env(safe-area-inset-bottom, 24px);
        }
        .card {
            background: rgba(28, 28, 30, 0.8);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
            padding: 40px 32px;
            border-radius: 28px;
            max-width: 380px;
            width: 100%;
        }
        .icon {
            width: 72px;
            height: 72px;
            background: rgba(10, 132, 255, 0.15);
            border: 2px solid #0a84ff;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px auto;
            color: #0a84ff;
        }
        h2 { font-size: 1.45rem; margin-bottom: 8px; font-weight: 700; letter-spacing: -0.02em; }
        p { color: #8e8e93; font-size: 0.95rem; margin-bottom: 28px; line-height: 1.5; }
        button {
            background: #0a84ff;
            color: #ffffff;
            border: 0;
            padding: 14px 28px;
            border-radius: 14px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 4px 18px rgba(10, 132, 255, 0.35);
            transition: transform 0.15s ease, opacity 0.15s ease;
        }
        button:active {
            transform: scale(0.97);
            opacity: 0.85;
        }
        .status {
            font-size: 0.8rem;
            color: #636366;
            margin-top: 16px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">
            <svg width="36" height="36" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 4.243a9 9 0 01-6.364-2.636M3 3l18 18M9.879 9.879a3 3 0 004.242 4.242M6.343 6.343A9 9 0 003 12c0 2.485 1.007 4.735 2.636 6.364" />
            </svg>
        </div>
        <h2>Connection Lost</h2>
        <p>Your device appears to be offline. Check your Wi-Fi or cellular network connection and try again.</p>
        <button id="retry-btn" onclick="retry()">Try Again</button>
        <div class="status" id="status-txt">Waiting for network...</div>
    </div>
    <script>
        function retry() {
            var txt = document.getElementById('status-txt');
            if (txt) txt.innerText = 'Reconnecting...';
            try {
                if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.iOSApp) {
                    window.webkit.messageHandlers.iOSApp.postMessage({action: "retry"});
                    return;
                }
            } catch(e) {}
            window.location.reload();
        }
        window.addEventListener('online', function() {
            var txt = document.getElementById('status-txt');
            if (txt) txt.innerText = 'Network restored! Reconnecting...';
            setTimeout(retry, 800);
        });
    </script>
</body>
</html>
"""

class TemplateEngine:
    """
    Synthesizes modern, production-grade Swift & Xcode projects for iOS.
    Features:
      - WKWebView with inline media, full JavaScript bridge, and safe area insets.
      - Fullscreen video playback with AVPlayer integration.
      - Pull-to-refresh & back/forward gesture navigation.
      - External app URL scheme handlers (WhatsApp, tel, mailto, maps).
      - Resilient offline fallback handling.
      - Hardware haptics and native share sheet triggers via WebKit message handlers.
      - Apple Asset Catalog and Info.plist with automatically detected privacy descriptions.
    """

    @classmethod
    def generate_project(
        cls,
        target_dir: str,
        app_name: str,
        bundle_id: str,
        version_name: str = "1.0.0",
        version_code: int = 1,
        remote_url: Optional[str] = None,
        is_fullscreen: bool = False,
        screen_orientation: str = "sensor",
        theme_color: str = "#000000",
        extra_permissions: Optional[List[str]] = None,
        custom_icon_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a complete, buildable Xcode project directory with Swift source code.
        """
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        clean_slug = re.sub(r'[^a-zA-Z0-9]', '', app_name) or "App"
        app_folder = target_path / clean_slug
        app_folder.mkdir(parents=True, exist_ok=True)

        # 1. Generate Info.plist
        cls._generate_info_plist(
            output_path=app_folder / "Info.plist",
            app_name=app_name,
            bundle_id=bundle_id,
            version_name=version_name,
            version_code=version_code,
            is_fullscreen=is_fullscreen,
            screen_orientation=screen_orientation,
            permissions=extra_permissions or []
        )

        # 2. Generate AppDelegate.swift
        cls._generate_app_delegate(app_folder / "AppDelegate.swift", app_name)

        # 3. Generate SceneDelegate.swift
        cls._generate_scene_delegate(app_folder / "SceneDelegate.swift", clean_slug)

        # 4. Generate WebViewController.swift
        cls._generate_web_view_controller(
            output_path=app_folder / "WebViewController.swift",
            app_name=app_name,
            remote_url=remote_url,
            is_fullscreen=is_fullscreen,
            theme_color=theme_color
        )

        # 5. Generate Offline HTML fallback
        offline_file = app_folder / "offline.html"
        offline_file.write_text(OFFLINE_HTML, encoding="utf-8")

        # 6. Generate Assets.xcassets
        xcassets_dir = app_folder / "Assets.xcassets"
        cls._generate_asset_catalog(xcassets_dir, theme_color, custom_icon_path, app_name)

        # 7. Generate project.pbxproj
        proj_dir = target_path / f"{clean_slug}.xcodeproj"
        proj_dir.mkdir(parents=True, exist_ok=True)
        cls._generate_pbxproj(
            output_path=proj_dir / "project.pbxproj",
            app_name=clean_slug,
            bundle_id=bundle_id,
            version_name=version_name,
            version_code=version_code
        )

        return {
            "success": True,
            "project_dir": str(target_path),
            "app_folder": str(app_folder),
            "xcodeproj_path": str(proj_dir),
            "app_slug": clean_slug
        }

    @classmethod
    def _generate_info_plist(
        cls,
        output_path: Path,
        app_name: str,
        bundle_id: str,
        version_name: str,
        version_code: int,
        is_fullscreen: bool,
        screen_orientation: str,
        permissions: List[str]
    ):
        orientations_phone = ["UIInterfaceOrientationPortrait"]
        orientations_pad = ["UIInterfaceOrientationPortrait", "UIInterfaceOrientationPortraitUpsideDown", "UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"]

        if screen_orientation == "landscape":
            orientations_phone = ["UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"]
            orientations_pad = ["UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"]
        elif screen_orientation in ["sensor", "all", "unspecified"]:
            orientations_phone = ["UIInterfaceOrientationPortrait", "UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"]

        phone_orientations_xml = "\n".join(f"        <string>{o}</string>" for o in orientations_phone)
        pad_orientations_xml = "\n".join(f"        <string>{o}</string>" for o in orientations_pad)

        # Permission descriptions
        perm_xml_parts = []
        perm_map = {
            "NSCameraUsageDescription": f"{app_name} needs camera access to capture photos and scan documents.",
            "NSMicrophoneUsageDescription": f"{app_name} needs microphone access for voice input and recording audio.",
            "NSLocationWhenInUseUsageDescription": f"{app_name} requires your location to provide personalized, localized services.",
            "NSPhotoLibraryAddUsageDescription": f"{app_name} needs permission to save images to your photo library.",
            "NSPhotoLibraryUsageDescription": f"{app_name} needs photo library access to upload photos and media."
        }

        for p in permissions:
            desc = perm_map.get(p, f"{app_name} requires permission for {p}.")
            perm_xml_parts.append(f"    <key>{p}</key>\n    <string>{desc}</string>")

        perm_xml = "\n".join(perm_xml_parts)
        if perm_xml:
            perm_xml = "\n" + perm_xml

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>{app_name}</string>
    <key>CFBundleExecutable</key>
    <string>$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key>
    <string>{bundle_id}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{version_name}</string>
    <key>CFBundleVersion</key>
    <string>{version_code}</string>
    <key>LSRequiresIPhoneOS</key>
    <true/>
    <key>UIRequiresFullScreen</key>
    <{"true" if is_fullscreen else "false"}/>
    <key>UIViewControllerBasedStatusBarAppearance</key>
    <false/>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
        <key>NSAllowsLocalNetworking</key>
        <true/>
    </dict>
    <key>UIApplicationSceneManifest</key>
    <dict>
        <key>UIApplicationSupportsMultipleScenes</key>
        <false/>
        <key>UISceneConfigurations</key>
        <dict>
            <key>UIWindowSceneSessionRoleApplication</key>
            <array>
                <dict>
                    <key>UISceneConfigurationName</key>
                    <string>Default Configuration</string>
                    <key>UISceneDelegateClassName</key>
                    <string>$(PRODUCT_MODULE_NAME).SceneDelegate</string>
                </dict>
            </array>
        </dict>
    </dict>
    <key>UILaunchScreen</key>
    <dict/>
    <key>UISupportedInterfaceOrientations</key>
    <array>
{phone_orientations_xml}
    </array>
    <key>UISupportedInterfaceOrientations~ipad</key>
    <array>
{pad_orientations_xml}
    </array>{perm_xml}
</dict>
</plist>
"""
        output_path.write_text(plist_content.strip(), encoding="utf-8")

    @classmethod
    def _generate_app_delegate(cls, output_path: Path, app_name: str):
        content = """//
//  AppDelegate.swift
//  __APP_NAME__
//
//  Generated by Web2IPA AI Agent
//

import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        return true
    }

    // MARK: UISceneSession Lifecycle

    func application(_ application: UIApplication, configurationForConnecting connectingSceneSession: UISceneSession, options: UIScene.ConnectionOptions) -> UISceneConfiguration {
        return UISceneConfiguration(name: "Default Configuration", sessionRole: connectingSceneSession.role)
    }

    func application(_ application: UIApplication, didDiscardSceneSessions sceneSessions: Set<UISceneSession>) {
    }
}
""".replace("__APP_NAME__", app_name)
        output_path.write_text(content.strip(), encoding="utf-8")

    @classmethod
    def _generate_scene_delegate(cls, output_path: Path, clean_slug: str):
        content = """//
//  SceneDelegate.swift
//  __SLUG__
//
//  Generated by Web2IPA AI Agent
//

import UIKit

class SceneDelegate: UIResponder, UIWindowSceneDelegate {

    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = (scene as? UIWindowScene) else { return }

        let window = UIWindow(windowScene: windowScene)
        let rootVC = WebViewController()
        window.rootViewController = rootVC
        self.window = window
        window.makeKeyAndVisible()
    }

    func sceneDidDisconnect(_ scene: UIScene) {}
    func sceneDidBecomeActive(_ scene: UIScene) {}
    func sceneWillResignActive(_ scene: UIScene) {}
    func sceneWillEnterForeground(_ scene: UIScene) {}
    func sceneDidEnterBackground(_ scene: UIScene) {}
}
""".replace("__SLUG__", clean_slug)
        output_path.write_text(content.strip(), encoding="utf-8")

    @classmethod
    def _generate_web_view_controller(
        cls,
        output_path: Path,
        app_name: str,
        remote_url: Optional[str],
        is_fullscreen: bool,
        theme_color: str
    ):
        if remote_url:
            target_load_logic = f"""
        if let url = URL(string: "{remote_url}") {{
            let request = URLRequest(url: url, cachePolicy: .returnCacheDataElseLoad, timeoutInterval: 20.0)
            webView.load(request)
        }} else {{
            loadOfflineFallback()
        }}
"""
        else:
            target_load_logic = """
        if let localUrl = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "www") {
            webView.loadFileURL(localUrl, allowingReadAccessTo: localUrl.deletingLastPathComponent())
        } else if let altUrl = Bundle.main.url(forResource: "index", withExtension: "html") {
            webView.loadFileURL(altUrl, allowingReadAccessTo: altUrl.deletingLastPathComponent())
        } else {
            loadOfflineFallback()
        }
"""

        swift_template = """//
//  WebViewController.swift
//  __APP_NAME__
//
//  Generated by Web2IPA AI Agent
//

import UIKit
import WebKit
import AVKit

class WebViewController: UIViewController, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {

    var webView: WKWebView!
    var progressView: UIProgressView!
    var refreshControl: UIRefreshControl!
    private var progressObserver: NSKeyValueObservation?

    override var prefersStatusBarHidden: Bool {
        return __FULLSCREEN__
    }

    override var preferredStatusBarStyle: UIStatusBarStyle {
        return .lightContent
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        setupWebView()
        setupProgressBar()
        loadContent()
    }

    private func setupUI() {
        view.backgroundColor = UIColor(hex: "__THEME_COLOR__") ?? .black
    }

    private func setupWebView() {
        let contentController = WKUserContentController()
        contentController.add(self, name: "iOSApp")

        let downloadBridgeJS = \"\"\"
        (function() {
            if (window.__web2ipa_download_interceptor) return;
            window.__web2ipa_download_interceptor = true;
            window.__blob_cache = window.__blob_cache || {};
            try {
                var origCreate = URL.createObjectURL;
                if (origCreate) {
                    URL.createObjectURL = function(blob) {
                        var u = origCreate.call(URL, blob);
                        window.__blob_cache[u] = blob;
                        return u;
                    };
                }
                var origRevoke = URL.revokeObjectURL;
                if (origRevoke) {
                    URL.revokeObjectURL = function(u) {
                        setTimeout(function() {
                            delete window.__blob_cache[u];
                            try { origRevoke.call(URL, u); } catch(e){}
                        }, 30000);
                    };
                }
            } catch(e) {}
            var dbExts = ['.sqlite','.sqlite3','.db','.db3','.s3db','.sl3','.sql','.dump','.bak','.backup','.json','.csv','.tsv','.xlsx','.xls','.xml','.parquet','.zip','.tar','.gz','.7z','.rar','.bin','.dat','.pdf','.txt'];
            function isDb(u, f) {
                var s = ((f || '') + ' ' + (u || '')).toLowerCase();
                for (var i = 0; i < dbExts.length; i++) { if (s.indexOf(dbExts[i]) !== -1) return true; }
                return false;
            }
            function sendToNative(action, payload) {
                try {
                    if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.iOSApp) {
                        payload.action = action;
                        window.webkit.messageHandlers.iOSApp.postMessage(payload);
                        return true;
                    }
                } catch(e) {}
                return false;
            }
            function procBlob(b, name) {
                var reader = new FileReader();
                reader.onloadend = function() {
                    sendToNative('saveFile', { base64: reader.result, filename: name || 'database.sqlite', mimeType: b.type || '' });
                };
                reader.readAsDataURL(b);
            }
            function trig(u, name) {
                if (!u) return false;
                if (u.indexOf('blob:') === 0) {
                    var cached = (window.__blob_cache && window.__blob_cache[u]) ? window.__blob_cache[u] : null;
                    if (cached) {
                        procBlob(cached, name);
                    } else {
                        fetch(u).then(function(r) { return r.blob(); }).then(function(b) { procBlob(b, name); }).catch(function() {});
                    }
                    return true;
                } else if (u.indexOf('data:') === 0) {
                    return sendToNative('saveFile', { base64: u, filename: name || 'database.sqlite', mimeType: '' });
                } else if (isDb(u, name) || name) {
                    return sendToNative('downloadUrl', { url: u, filename: name || '', mimeType: '' });
                }
                return false;
            }
            document.addEventListener('click', function(e) {
                var t = e.target;
                while (t && t.tagName !== 'A') t = t.parentElement;
                if (!t || t.tagName !== 'A') return;
                var h = t.getAttribute('href') || t.href || '';
                var d = t.getAttribute('download');
                var fn = d || t.download || '';
                if (d !== null || h.indexOf('blob:') === 0 || h.indexOf('data:') === 0 || isDb(h, fn)) {
                    if (trig(h, fn)) { e.preventDefault(); e.stopPropagation(); }
                }
            }, true);
            try {
                var origClick = HTMLAnchorElement.prototype.click;
                HTMLAnchorElement.prototype.click = function() {
                    var h = this.getAttribute('href') || this.href || '';
                    var d = this.getAttribute('download');
                    var fn = d || this.download || '';
                    if (d !== null || h.indexOf('blob:') === 0 || h.indexOf('data:') === 0 || isDb(h, fn)) {
                        if (trig(h, fn)) return;
                    }
                    return origClick.apply(this, arguments);
                };
            } catch(e) {}
        })();
        \"\"\"
        let userScript = WKUserScript(source: downloadBridgeJS, injectionTime: .atDocumentEnd, forMainFrameOnly: false)
        contentController.addUserScript(userScript)

        let config = WKWebViewConfiguration()
        config.userContentController = contentController
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        config.preferences.javaScriptCanOpenWindowsAutomatically = true
        if #available(iOS 15.4, *) {
            config.preferences.isElementFullscreenEnabled = true
        }

        webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        webView.scrollView.contentInsetAdjustmentBehavior = .always
        webView.isOpaque = false
        webView.backgroundColor = .clear

        // Pull to refresh
        refreshControl = UIRefreshControl()
        refreshControl.addTarget(self, action: #selector(handleRefresh), for: .valueChanged)
        webView.scrollView.refreshControl = refreshControl

        view.addSubview(webView)
        webView.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: view.topAnchor),
            webView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            webView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.trailingAnchor)
        ])
    }

    private func setupProgressBar() {
        progressView = UIProgressView(progressViewStyle: .bar)
        progressView.tintColor = UIColor(hex: "#0a84ff") ?? .systemBlue
        progressView.trackTintColor = .clear
        view.addSubview(progressView)
        progressView.translatesAutoresizingMaskIntoConstraints = false

        NSLayoutConstraint.activate([
            progressView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            progressView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            progressView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            progressView.heightAnchor.constraint(equalToConstant: 2.5)
        ])

        progressObserver = webView.observe(\\.estimatedProgress, options: [.new]) { [weak self] _, change in
            guard let self = self, let progress = change.newValue else { return }
            self.progressView.progress = Float(progress)
            self.progressView.isHidden = progress >= 1.0
        }
    }

    @objc private func handleRefresh() {
        webView.reload()
    }

    private func loadContent() {
__LOAD_LOGIC__
    }

    private func loadOfflineFallback() {
        if let offlineUrl = Bundle.main.url(forResource: "offline", withExtension: "html") {
            webView.loadFileURL(offlineUrl, allowingReadAccessTo: offlineUrl.deletingLastPathComponent())
        }
    }

    // MARK: - WKNavigationDelegate

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        refreshControl.endRefreshing()
        progressView.isHidden = true
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        refreshControl.endRefreshing()
        progressView.isHidden = true
        let nsError = error as NSError
        if nsError.code != NSURLErrorCancelled {
            loadOfflineFallback()
        }
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        refreshControl.endRefreshing()
        progressView.isHidden = true
        let nsError = error as NSError
        if nsError.code != NSURLErrorCancelled {
            loadOfflineFallback()
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.allow)
            return
        }

        let scheme = url.scheme?.lowercased() ?? ""
        // Handle external schemes (WhatsApp, phone, mail, SMS, Maps)
        if ["tel", "mailto", "sms", "facetime", "whatsapp"].contains(scheme) || url.host == "wa.me" || url.host == "api.whatsapp.com" {
            if UIApplication.shared.canOpenURL(url) {
                UIApplication.shared.open(url, options: [:], completionHandler: nil)
                decisionHandler(.cancel)
                return
            }
        }

        let lowerUrl = url.absoluteString.lowercased()
        let dbExts = [".sqlite", ".sqlite3", ".db", ".db3", ".sql", ".dump", ".bak", ".parquet", ".csv", ".tsv", ".xlsx", ".zip"]
        if dbExts.contains(where: { lowerUrl.hasSuffix($0) }) {
            self.downloadAndShare(url: url, suggestedName: url.lastPathComponent)
            decisionHandler(.cancel)
            return
        }

        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationResponse: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        if let response = navigationResponse.response as? HTTPURLResponse {
            let disp = (response.allHeaderFields["Content-Disposition"] as? String ?? "").lowercased()
            let urlStr = response.url?.absoluteString.lowercased() ?? ""
            let isDbExt = [".sqlite", ".sqlite3", ".db", ".db3", ".sql", ".dump", ".bak", ".parquet", ".csv", ".tsv", ".xlsx", ".zip"].contains(where: { urlStr.hasSuffix($0) })
            let isAttachment = disp.contains("attachment") || !navigationResponse.canShowMIMEType || isDbExt
            
            if isAttachment, let downloadUrl = response.url {
                decisionHandler(.cancel)
                var filename = "database_export.sqlite"
                if let rawDisp = response.allHeaderFields["Content-Disposition"] as? String,
                   let range = rawDisp.range(of: "filename=") {
                    let extracted = String(rawDisp[range.upperBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "\"' ;"))
                    if !extracted.isEmpty { filename = extracted }
                } else if !downloadUrl.lastPathComponent.isEmpty && !downloadUrl.lastPathComponent.hasSuffix(".html") {
                    filename = downloadUrl.lastPathComponent
                }
                self.downloadAndShare(url: downloadUrl, suggestedName: filename)
                return
            }
        }
        decisionHandler(.allow)
    }

    private func downloadAndShare(url: URL, suggestedName: String) {
        WKWebsiteDataStore.default().httpCookieStore.getAllCookies { cookies in
            var request = URLRequest(url: url)
            let cookieHeaders = HTTPCookie.requestHeaderFields(with: cookies)
            for (header, val) in cookieHeaders {
                request.addValue(val, forHTTPHeaderField: header)
            }
            let task = URLSession.shared.dataTask(with: request) { data, response, error in
                guard let data = data, error == nil else { return }
                var finalName = suggestedName.isEmpty ? "database_export.sqlite" : suggestedName
                if let httpResp = response as? HTTPURLResponse,
                   let disp = httpResp.allHeaderFields["Content-Disposition"] as? String,
                   let range = disp.range(of: "filename=") {
                    let extracted = String(disp[range.upperBound...]).trimmingCharacters(in: CharacterSet(charactersIn: "\"' ;"))
                    if !extracted.isEmpty { finalName = extracted }
                }
                let isSqlite = data.count >= 16 && String(decoding: data.prefix(16), as: UTF8.self).starts(with: "SQLite format 3")
                let lower = finalName.lowercased()
                if isSqlite && !lower.hasSuffix(".sqlite") && !lower.hasSuffix(".db") {
                    finalName = (finalName as NSString).deletingPathExtension + ".sqlite"
                }
                let tempUrl = FileManager.default.temporaryDirectory.appendingPathComponent(finalName)
                try? data.write(to: tempUrl)
                DispatchQueue.main.async {
                    let activityVC = UIActivityViewController(activityItems: [tempUrl], applicationActivities: nil)
                    if let popover = activityVC.popoverPresentationController {
                        popover.sourceView = self.view
                        popover.sourceRect = CGRect(x: self.view.bounds.midX, y: self.view.bounds.midY, width: 0, height: 0)
                        popover.permittedArrowDirections = []
                    }
                    self.present(activityVC, animated: true)
                    let feedback = UINotificationFeedbackGenerator()
                    feedback.notificationOccurred(.success)
                }
            }
            task.resume()
        }
    }

    // MARK: - WKUIDelegate

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if navigationAction.targetFrame == nil {
            webView.load(navigationAction.request)
        }
        return nil
    }

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler() })
        present(alert, animated: true, completion: nil)
    }

    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel) { _ in completionHandler(false) })
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler(true) })
        present(alert, animated: true, completion: nil)
    }

    // MARK: - WKScriptMessageHandler (Bridge to Native iOS)

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "iOSApp", let body = message.body as? [String: Any] else { return }
        
        let action = body["action"] as? String ?? ""
        
        switch action {
        case "retry", "refresh":
            loadContent()
        case "haptic":
            let style = body["style"] as? String ?? "medium"
            let generator = UIImpactFeedbackGenerator(style: style == "heavy" ? .heavy : style == "light" ? .light : .medium)
            generator.impactOccurred()
        case "share":
            if let text = body["text"] as? String {
                var items: [Any] = [text]
                if let urlStr = body["url"] as? String, let shareUrl = URL(string: urlStr) {
                    items.append(shareUrl)
                }
                let activityVC = UIActivityViewController(activityItems: items, applicationActivities: nil)
                present(activityVC, animated: true)
            }
        case "saveFile":
            guard let base64Raw = body["base64"] as? String else { return }
            let suggestedName = (body["filename"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "database_export"
            
            var cleanBase64 = base64Raw
            if let commaIndex = cleanBase64.firstIndex(of: ",") {
                cleanBase64 = String(cleanBase64[cleanBase64.index(after: commaIndex)...])
            }
            cleanBase64 = cleanBase64.replacingOccurrences(of: "\\s+", with: "", options: .regularExpression)
            
            guard let fileData = Data(base64Encoded: cleanBase64) else { return }
            
            var finalName = suggestedName.isEmpty ? "database_export" : suggestedName
            var isSqlite = false
            if fileData.count >= 16 {
                let header = String(decoding: fileData.prefix(16), as: UTF8.self)
                if header.starts(with: "SQLite format 3") {
                    isSqlite = true
                }
            }
            let isZip = fileData.count >= 4 && fileData[0] == 0x50 && fileData[1] == 0x4B && fileData[2] == 0x03 && fileData[3] == 0x04
            let lower = finalName.lowercased()
            if isSqlite && !lower.hasSuffix(".sqlite") && !lower.hasSuffix(".db") && !lower.hasSuffix(".sqlite3") {
                finalName = (finalName as NSString).deletingPathExtension + ".sqlite"
            } else if isZip && !lower.hasSuffix(".zip") {
                finalName = (finalName as NSString).deletingPathExtension + ".zip"
            } else if lower.hasSuffix(".html") || lower.hasSuffix(".htm") || !lower.contains(".") {
                if let snippet = String(data: fileData.prefix(256), encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) {
                    if snippet.starts(with: "{") || snippet.starts(with: "[") {
                        finalName = (finalName as NSString).deletingPathExtension + ".json"
                    } else if snippet.uppercased().starts(with: "CREATE ") || snippet.uppercased().starts(with: "INSERT ") || snippet.starts(with: "--") || snippet.starts(with: "/*") {
                        finalName = (finalName as NSString).deletingPathExtension + ".sql"
                    } else if snippet.contains(",") {
                        finalName = (finalName as NSString).deletingPathExtension + ".csv"
                    } else if isSqlite {
                        finalName = (finalName as NSString).deletingPathExtension + ".sqlite"
                    }
                }
            }
            
            let tempDir = FileManager.default.temporaryDirectory
            let targetUrl = tempDir.appendingPathComponent(finalName)
            do {
                try fileData.write(to: targetUrl)
                DispatchQueue.main.async {
                    let activityVC = UIActivityViewController(activityItems: [targetUrl], applicationActivities: nil)
                    if let popover = activityVC.popoverPresentationController {
                        popover.sourceView = self.view
                        popover.sourceRect = CGRect(x: self.view.bounds.midX, y: self.view.bounds.midY, width: 0, height: 0)
                        popover.permittedArrowDirections = []
                    }
                    self.present(activityVC, animated: true)
                    let feedback = UINotificationFeedbackGenerator()
                    feedback.notificationOccurred(.success)
                }
            } catch {
                print("[Web2IPA] Error saving file:", error)
            }

        case "downloadUrl":
            guard let urlStr = body["url"] as? String, let downloadUrl = URL(string: urlStr) else { return }
            let sName = (body["filename"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            self.downloadAndShare(url: downloadUrl, suggestedName: sName)

        default:
            break
        }
    }
}

// MARK: - Color Hex Extension
extension UIColor {
    convenience init?(hex: String) {
        var hexSanitized = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        hexSanitized = hexSanitized.replacingOccurrences(of: "#", with: "")

        var rgb: UInt64 = 0
        guard Scanner(string: hexSanitized).scanHexInt64(&rgb) else { return nil }

        let r, g, b, a: CGFloat
        let length = hexSanitized.count

        if length == 6 {
            r = CGFloat((rgb & 0xFF0000) >> 16) / 255.0
            g = CGFloat((rgb & 0x00FF00) >> 8) / 255.0
            b = CGFloat(rgb & 0x0000FF) / 255.0
            a = 1.0
            self.init(red: r, green: g, blue: b, alpha: a)
        } else if length == 8 {
            r = CGFloat((rgb & 0xFF000000) >> 24) / 255.0
            g = CGFloat((rgb & 0x00FF0000) >> 16) / 255.0
            b = CGFloat((rgb & 0x0000FF00) >> 8) / 255.0
            a = CGFloat(rgb & 0x000000FF) / 255.0
            self.init(red: r, green: g, blue: b, alpha: a)
        } else {
            return nil
        }
    }
}
"""
        content = swift_template \
            .replace("__APP_NAME__", app_name) \
            .replace("__FULLSCREEN__", "true" if is_fullscreen else "false") \
            .replace("__THEME_COLOR__", theme_color) \
            .replace("__LOAD_LOGIC__", target_load_logic)

        output_path.write_text(content.strip(), encoding="utf-8")

    @classmethod
    def _generate_asset_catalog(
        cls,
        xcassets_dir: Path,
        theme_color: str,
        custom_icon_path: Optional[str],
        app_name: str
    ):
        xcassets_dir.mkdir(parents=True, exist_ok=True)
        # Root Contents.json
        (xcassets_dir / "Contents.json").write_text("""{
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}
""", encoding="utf-8")

        # AccentColor.colorset
        accent_dir = xcassets_dir / "AccentColor.colorset"
        accent_dir.mkdir(parents=True, exist_ok=True)
        (accent_dir / "Contents.json").write_text("""{
  "colors" : [
    {
      "idiom" : "universal"
    }
  ],
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}
""", encoding="utf-8")

        # AppIcon.appiconset
        from .icon_generator import iOSIconGenerator
        appicon_dir = xcassets_dir / "AppIcon.appiconset"
        iOSIconGenerator.generate_apple_icon_catalog(
            output_dir=appicon_dir,
            source_icon_path=custom_icon_path,
            app_name=app_name,
            theme_color=theme_color
        )

    @classmethod
    def _generate_pbxproj(
        cls,
        output_path: Path,
        app_name: str,
        bundle_id: str,
        version_name: str,
        version_code: int
    ):
        """
        Synthesizes a fully valid OpenStep PBXProject file accepted by Xcode 14, 15, and 16.
        """
        def uid(prefix: str) -> str:
            return f"{prefix}{uuid.uuid4().hex[:16].upper()}"

        proj_uuid = uid("PRJ")
        target_uuid = uid("TAR")
        config_list_proj = uid("CLP")
        config_list_tar = uid("CLT")
        main_group_uuid = uid("MGP")
        app_group_uuid = uid("AGP")
        products_group_uuid = uid("PGP")
        product_file_uuid = uid("PFL")

        # Build phases
        sources_phase_uuid = uid("SRC")
        resources_phase_uuid = uid("RES")
        frameworks_phase_uuid = uid("FRM")

        # Files
        files = {
            "AppDelegate.swift": (uid("FAD"), uid("BAD")),
            "SceneDelegate.swift": (uid("FSD"), uid("BSD")),
            "WebViewController.swift": (uid("FWV"), uid("BWV")),
            "Info.plist": (uid("FIP"), None),
            "offline.html": (uid("FOH"), uid("BOH")),
            "Assets.xcassets": (uid("FAX"), uid("BAX")),
        }

        # Build Configurations
        debug_proj_cfg = uid("DPC")
        release_proj_cfg = uid("RPC")
        debug_tar_cfg = uid("DTC")
        release_tar_cfg = uid("RTC")

        pbx_content = f"""// !$*UTF8*$!
{{
	archiveVersion = 1;
	classes = {{
	}};
	objectVersion = 54;
	objects = {{

/* Begin PBXBuildFile section */
		{files["AppDelegate.swift"][1]} /* AppDelegate.swift in Sources */ = {{isa = PBXBuildFile; fileRef = {files["AppDelegate.swift"][0]} /* AppDelegate.swift */; }};
		{files["SceneDelegate.swift"][1]} /* SceneDelegate.swift in Sources */ = {{isa = PBXBuildFile; fileRef = {files["SceneDelegate.swift"][0]} /* SceneDelegate.swift */; }};
		{files["WebViewController.swift"][1]} /* WebViewController.swift in Sources */ = {{isa = PBXBuildFile; fileRef = {files["WebViewController.swift"][0]} /* WebViewController.swift */; }};
		{files["offline.html"][1]} /* offline.html in Resources */ = {{isa = PBXBuildFile; fileRef = {files["offline.html"][0]} /* offline.html */; }};
		{files["Assets.xcassets"][1]} /* Assets.xcassets in Resources */ = {{isa = PBXBuildFile; fileRef = {files["Assets.xcassets"][0]} /* Assets.xcassets */; }};
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
		{product_file_uuid} /* {app_name}.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = "{app_name}.app"; sourceTree = BUILT_PRODUCTS_DIR; }};
		{files["AppDelegate.swift"][0]} /* AppDelegate.swift */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = AppDelegate.swift; sourceTree = "<group>"; }};
		{files["SceneDelegate.swift"][0]} /* SceneDelegate.swift */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = SceneDelegate.swift; sourceTree = "<group>"; }};
		{files["WebViewController.swift"][0]} /* WebViewController.swift */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = WebViewController.swift; sourceTree = "<group>"; }};
		{files["Info.plist"][0]} /* Info.plist */ = {{isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>"; }};
		{files["offline.html"][0]} /* offline.html */ = {{isa = PBXFileReference; lastKnownFileType = text.html; path = offline.html; sourceTree = "<group>"; }};
		{files["Assets.xcassets"][0]} /* Assets.xcassets */ = {{isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = Assets.xcassets; sourceTree = "<group>"; }};
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
		{frameworks_phase_uuid} /* Frameworks */ = {{
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
		{main_group_uuid} = {{
			isa = PBXGroup;
			children = (
				{app_group_uuid} /* {app_name} */,
				{products_group_uuid} /* Products */,
			);
			sourceTree = "<group>";
		}};
		{app_group_uuid} /* {app_name} */ = {{
			isa = PBXGroup;
			children = (
				{files["AppDelegate.swift"][0]} /* AppDelegate.swift */,
				{files["SceneDelegate.swift"][0]} /* SceneDelegate.swift */,
				{files["WebViewController.swift"][0]} /* WebViewController.swift */,
				{files["offline.html"][0]} /* offline.html */,
				{files["Assets.xcassets"][0]} /* Assets.xcassets */,
				{files["Info.plist"][0]} /* Info.plist */,
			);
			path = {app_name};
			sourceTree = "<group>";
		}};
		{products_group_uuid} /* Products */ = {{
			isa = PBXGroup;
			children = (
				{product_file_uuid} /* {app_name}.app */,
			);
			name = Products;
			sourceTree = "<group>";
		}};
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
		{target_uuid} /* {app_name} */ = {{
			isa = PBXNativeTarget;
			buildConfigurationList = {config_list_tar} /* Build configuration list for PBXNativeTarget "{app_name}" */;
			buildPhases = (
				{sources_phase_uuid} /* Sources */,
				{frameworks_phase_uuid} /* Frameworks */,
				{resources_phase_uuid} /* Resources */,
			);
			buildRules = (
			);
			dependencies = (
			);
			name = {app_name};
			productName = {app_name};
			productReference = {product_file_uuid} /* {app_name}.app */;
			productType = "com.apple.product-type.application";
		}};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
		{proj_uuid} /* Project object */ = {{
			isa = PBXProject;
			attributes = {{
				BuildIndependentTargetsInParallel = 1;
				LastSwiftUpdateCheck = 1500;
				LastUpgradeCheck = 1500;
				TargetAttributes = {{
					{target_uuid} = {{
						CreatedOnToolsVersion = 15.0;
					}};
				}};
			}};
			buildConfigurationList = {config_list_proj} /* Build configuration list for PBXProject "{app_name}" */;
			compatibilityVersion = "Xcode 14.0";
			developmentRegion = en;
			hasScannedForEncodings = 0;
			knownRegions = (
				en,
				Base,
			);
			mainGroup = {main_group_uuid};
			productRefGroup = {products_group_uuid} /* Products */;
			projectDirPath = "";
			projectRoot = "";
			targets = (
				{target_uuid} /* {app_name} */,
			);
		}};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
		{resources_phase_uuid} /* Resources */ = {{
			isa = PBXResourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				{files["offline.html"][1]} /* offline.html in Resources */,
				{files["Assets.xcassets"][1]} /* Assets.xcassets in Resources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
		{sources_phase_uuid} /* Sources */ = {{
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				{files["AppDelegate.swift"][1]} /* AppDelegate.swift in Sources */,
				{files["SceneDelegate.swift"][1]} /* SceneDelegate.swift in Sources */,
				{files["WebViewController.swift"][1]} /* WebViewController.swift in Sources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
		{debug_proj_cfg} /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = dwarf;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				ENABLE_TESTABILITY = YES;
				GCC_DYNAMIC_NO_PIC = NO;
				GCC_OPTIMIZATION_LEVEL = 0;
				GCC_PREPROCESSOR_DEFINITIONS = (
					"DEBUG=1",
					"$(inherited)",
				);
				GCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;
				IPHONEOS_DEPLOYMENT_TARGET = 15.0;
				MTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;
				ONLY_ACTIVE_ARCH = YES;
				SDKROOT = iphoneos;
				SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;
				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
			}};
			name = Debug;
		}};
		{release_proj_cfg} /* Release */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
				ENABLE_NS_ASSERTIONS = NO;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				GCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;
				IPHONEOS_DEPLOYMENT_TARGET = 15.0;
				MTL_ENABLE_DEBUG_INFO = NO;
				SDKROOT = iphoneos;
				SWIFT_COMPILATION_MODE = wholemodule;
				SWIFT_OPTIMIZATION_LEVEL = "-O";
				VALIDATE_PRODUCT = YES;
			}};
			name = Release;
		}};
		{debug_tar_cfg} /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = {version_code};
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = "{app_name}/Info.plist";
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = {version_name};
				PRODUCT_BUNDLE_IDENTIFIER = "{bundle_id}";
				PRODUCT_NAME = "$(TARGET_NAME)";
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			}};
			name = Debug;
		}};
		{release_tar_cfg} /* Release */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = {version_code};
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = "{app_name}/Info.plist";
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = {version_name};
				PRODUCT_BUNDLE_IDENTIFIER = "{bundle_id}";
				PRODUCT_NAME = "$(TARGET_NAME)";
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			}};
			name = Release;
		}};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
		{config_list_proj} /* Build configuration list for PBXProject "{app_name}" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				{debug_proj_cfg} /* Debug */,
				{release_proj_cfg} /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		}};
		{config_list_tar} /* Build configuration list for PBXNativeTarget "{app_name}" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				{debug_tar_cfg} /* Debug */,
				{release_tar_cfg} /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		}};
/* End XCConfigurationList section */

	}};
	rootObject = {proj_uuid} /* Project object */;
}}
"""
        output_path.write_text(pbx_content.strip(), encoding="utf-8")

    @classmethod
    def zip_project(cls, project_dir: Path, output_zip_path: Path) -> Path:
        """
        Compresses the generated project folder into a clean ZIP archive ready for Mac or CI/CD.
        """
        output_zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zip_out:
            for root, dirs, files in os.walk(project_dir):
                for f in files:
                    full_file = Path(root) / f
                    rel_path = full_file.relative_to(project_dir)
                    zip_out.write(full_file, arcname=str(rel_path))
        return output_zip_path
