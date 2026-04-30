import Foundation

struct SupportMoment: Equatable {
    enum Tone {
        case calm
        case celebration
    }

    let title: String
    let detail: String
    let tone: Tone
}
