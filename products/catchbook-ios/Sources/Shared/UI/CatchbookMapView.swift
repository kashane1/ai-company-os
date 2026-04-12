import CoreLocation
import MapKit
import SwiftUI

struct CatchbookMapView<Item: Identifiable, AnnotationContent: View, OverlayContent: View>: View {
    @Binding private var position: MapCameraPosition

    private let entries: [Entry<Item>]
    private let annotationContent: (Item) -> AnnotationContent
    private let overlayContent: OverlayContent

    init(
        items: [Item],
        position: Binding<MapCameraPosition>,
        coordinate: @escaping (Item) -> CLLocationCoordinate2D?,
        @ViewBuilder annotationContent: @escaping (Item) -> AnnotationContent,
        @ViewBuilder overlay: () -> OverlayContent
    ) {
        _position = position
        entries = items.compactMap { item in
            guard let coordinate = coordinate(item) else { return nil }
            return Entry(item: item, coordinate: coordinate)
        }
        self.annotationContent = annotationContent
        overlayContent = overlay()
    }

    var body: some View {
        Map(position: $position) {
            ForEach(entries) { entry in
                Annotation("", coordinate: entry.coordinate, anchor: .bottom) {
                    annotationContent(entry.item)
                }
            }
        }
        .overlay(alignment: .center) {
            overlayContent
        }
    }
}

extension CatchbookMapView where OverlayContent == EmptyView {
    init(
        items: [Item],
        position: Binding<MapCameraPosition>,
        coordinate: @escaping (Item) -> CLLocationCoordinate2D?,
        @ViewBuilder annotationContent: @escaping (Item) -> AnnotationContent
    ) {
        self.init(
            items: items,
            position: position,
            coordinate: coordinate,
            annotationContent: annotationContent,
            overlay: { EmptyView() }
        )
    }
}

private struct Entry<Item: Identifiable>: Identifiable {
    let item: Item
    let coordinate: CLLocationCoordinate2D

    var id: Item.ID { item.id }
}
