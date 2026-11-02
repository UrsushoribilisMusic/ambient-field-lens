import MWDATCore
import SwiftUI

@main
struct AmbientFieldLensApp: App {
    init() {
        // Always configure first, like the DisplayAccess sample. Mock is
        // enabled later at runtime (DemoSetup / Setup sheet), never here:
        // MockDeviceKit.enable() without a configured SDK traps (SIGTRAP
        // in MWDATCore), which is what crashed the test host.
        // Pure unit tests never touch Wearables.shared, so configure alone
        // is enough for the host to launch.
        do {
            try Wearables.configure()
            WearablesViewModel.sdkAvailable = true
        } catch {
            WearablesViewModel.sdkAvailable = false
            #if DEBUG
                NSLog("[AFL] Wearables configure failed: \(error)")
            #endif
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
