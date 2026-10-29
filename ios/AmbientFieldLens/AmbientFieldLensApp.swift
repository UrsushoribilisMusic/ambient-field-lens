import MWDATCore
import SwiftUI

@main
struct AmbientFieldLensApp: App {
    init() {
        // Unit-test host launches the app binary too; the simulator has no
        // Wearables transport, so configuration traps there. FrameSource and
        // other pure tests never touch the SDK — skip it under XCTest only.
        // Production launch path is unchanged.
        #if DEBUG
            if NSClassFromString("XCTestCase") != nil { return }
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
