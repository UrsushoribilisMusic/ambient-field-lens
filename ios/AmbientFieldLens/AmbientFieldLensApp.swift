import MWDATCore
import MWDATMockDevice
import SwiftUI

@main
struct AmbientFieldLensApp: App {
    init() {
        // Unit-test host launches the app binary too, and the host builds
        // ContentView -> WearablesViewModel -> Wearables.shared at startup,
        // which traps unless DAT is configured. The simulator has no
        // Wearables transport so the real configure() traps there; the mock
        // kit configures DAT itself instead. Enable it with no device paired
        // (nothing streams) so the host can launch and the pure tests run.
        // Production launch path is unchanged.
        #if DEBUG
            if NSClassFromString("XCTestCase") != nil {
                MockDeviceKit.shared.enable()
                return
            }
        #endif
        do {
            try Wearables.configure()
        } catch {
            assertionFailure("Wearables SDK configuration failed: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .onOpenURL { url in
                    guard
                        let components = URLComponents(
                            url: url, resolvingAgainstBaseURL: false
                        ),
                        components.queryItems?.contains(where: {
                            $0.name == "metaWearablesAction"
                        }) == true
                    else {
                        return
                    }
                    Task {
                        _ = try? await Wearables.shared.handleUrl(url)
                    }
                }
        }
    }
}
