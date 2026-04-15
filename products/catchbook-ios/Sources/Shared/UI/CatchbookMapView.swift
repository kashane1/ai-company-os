import CoreLocation
import MapKit
import SwiftUI

struct CatchbookMapView<Item: Identifiable, AnnotationContent: View, OverlayContent: View>: View {
    @AppStorage(CatchbookMapStyle.appStorageKey) private var storedMapStyle = CatchbookMapStyle.standard.rawValue
    @Binding private var position: MapCameraPosition

    private let entries: [Entry<Item>]
    private let annotationContent: (Item) -> AnnotationContent
    private let overlayContent: OverlayContent
    private let onCameraChange: ((CLLocationCoordinate2D) -> Void)?

    init(
        items: [Item],
        position: Binding<MapCameraPosition>,
        coordinate: @escaping (Item) -> CLLocationCoordinate2D?,
        onCameraChange: ((CLLocationCoordinate2D) -> Void)? = nil,
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
        self.onCameraChange = onCameraChange
    }

    var body: some View {
        Map(position: $position) {
            ForEach(entries) { entry in
                Annotation("", coordinate: entry.coordinate, anchor: .bottom) {
                    annotationContent(entry.item)
                }
            }
        }
        .onMapCameraChange(frequency: .continuous) { context in
            onCameraChange?(context.camera.centerCoordinate)
        }
        .mapStyle(selectedMapStyle.mapStyle)
        .overlay(alignment: .topTrailing) {
            Button {
                storedMapStyle = selectedMapStyle.next.rawValue
            } label: {
                Image(systemName: selectedMapStyle.iconName)
                    .font(.headline)
                    .foregroundStyle(Color.catchbookText)
                    .padding(10)
                    .background(.regularMaterial, in: Circle())
            }
            .padding(Spacing.md)
            .accessibilityLabel(selectedMapStyle.accessibilityLabel)
        }
        .overlay(alignment: .center) {
            overlayContent
        }
    }

    private var selectedMapStyle: CatchbookMapStyle {
        CatchbookMapStyle(rawValue: storedMapStyle) ?? .standard
    }
}

extension CatchbookMapView where OverlayContent == EmptyView {
    init(
        items: [Item],
        position: Binding<MapCameraPosition>,
        coordinate: @escaping (Item) -> CLLocationCoordinate2D?,
        onCameraChange: ((CLLocationCoordinate2D) -> Void)? = nil,
        @ViewBuilder annotationContent: @escaping (Item) -> AnnotationContent
    ) {
        self.init(
            items: items,
            position: position,
            coordinate: coordinate,
            onCameraChange: onCameraChange,
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
