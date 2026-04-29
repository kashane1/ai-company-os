import SwiftUI

/// Wraps subviews into rows, breaking to a new row when the proposed
/// width is exhausted. Designed for tag/pill pickers where each item
/// has its own intrinsic width.
///
/// Pass `.unspecified` to children — they size to intrinsic content.
/// Caches per-width row breakdown so `sizeThatFits` and `placeSubviews`
/// agree on the same layout in steady state.
struct FlowLayout: Layout {
    var hSpacing: CGFloat = Spacing.sm
    var vSpacing: CGFloat = Spacing.sm
    var alignment: HorizontalAlignment = .leading

    struct Cache {
        var rows: [[Int]] = []
        var rowSizes: [CGSize] = []
        var totalSize: CGSize = .zero
        var lastWidth: CGFloat = -1
    }

    func makeCache(subviews: Subviews) -> Cache { Cache() }

    func updateCache(_ cache: inout Cache, subviews: Subviews) {
        cache.lastWidth = -1
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout Cache) -> CGSize {
        let maxWidth = proposal.replacingUnspecifiedDimensions(
            by: CGSize(width: CGFloat.infinity, height: CGFloat.infinity)
        ).width
        compute(maxWidth: maxWidth, subviews: subviews, cache: &cache)
        return cache.totalSize
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout Cache) {
        compute(maxWidth: bounds.width, subviews: subviews, cache: &cache)
        var y = bounds.minY
        for (row, rowSize) in zip(cache.rows, cache.rowSizes) {
            let xStart: CGFloat = {
                switch alignment {
                case .center:   return bounds.minX + (bounds.width - rowSize.width) / 2
                case .trailing: return bounds.minX + (bounds.width - rowSize.width)
                default:        return bounds.minX
                }
            }()
            var x = xStart
            for index in row {
                let sub = subviews[index]
                let size = sub.sizeThatFits(.unspecified)
                sub.place(
                    at: CGPoint(x: x, y: y + (rowSize.height - size.height) / 2),
                    anchor: .topLeading,
                    proposal: ProposedViewSize(size)
                )
                x += size.width + hSpacing
            }
            y += rowSize.height + vSpacing
        }
    }

    private func compute(maxWidth: CGFloat, subviews: Subviews, cache: inout Cache) {
        guard cache.lastWidth != maxWidth else { return }
        cache.lastWidth = maxWidth
        cache.rows.removeAll(keepingCapacity: true)
        cache.rowSizes.removeAll(keepingCapacity: true)

        var currentRow: [Int] = []
        var rowWidth: CGFloat = 0
        var rowHeight: CGFloat = 0
        var totalHeight: CGFloat = 0
        var widestRow: CGFloat = 0

        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let needed = currentRow.isEmpty ? size.width : rowWidth + hSpacing + size.width
            if !currentRow.isEmpty && needed > maxWidth {
                cache.rows.append(currentRow)
                cache.rowSizes.append(CGSize(width: rowWidth, height: rowHeight))
                totalHeight += rowHeight + vSpacing
                widestRow = max(widestRow, rowWidth)
                currentRow = [index]
                rowWidth = size.width
                rowHeight = size.height
            } else {
                currentRow.append(index)
                rowWidth = needed
                rowHeight = max(rowHeight, size.height)
            }
        }
        if !currentRow.isEmpty {
            cache.rows.append(currentRow)
            cache.rowSizes.append(CGSize(width: rowWidth, height: rowHeight))
            totalHeight += rowHeight
            widestRow = max(widestRow, rowWidth)
        }
        cache.totalSize = CGSize(width: min(widestRow, maxWidth), height: totalHeight)
    }
}
