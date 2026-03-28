import { Hotel, Flight, ToolSnapshot, HotelSearchResult, FlightSearchResult, TravelTipsResult, HotelDetailResult, RoomType } from '../types'
// hotel click enabled
interface Props {
  snapshot: ToolSnapshot
  onHotelClick?: (hotelCode: string, hotelName: string) => void
}

export function ToolResultCard({ snapshot, onHotelClick }: Props) {
  const { tool, result } = snapshot

  if (tool === 'search_hotels') {
    return <HotelCard data={result as HotelSearchResult} onHotelClick={onHotelClick} />
  }
  if (tool === 'search_flights') {
    return <FlightCard data={result as FlightSearchResult} />
  }
  if (tool === 'get_travel_tips') {
    return <TipsCard data={result as TravelTipsResult} />
  }
  if (tool === 'get_hotel_detail') {
    return <HotelDetailCard data={result as HotelDetailResult} />
  }
  return null
}

// ── 호텔 카드 ──────────────────────────────────
function HotelCard({ data, onHotelClick }: { data: HotelSearchResult; onHotelClick?: (hotelCode: string, hotelName: string) => void }) {
  if (data.status !== 'success' || !data.hotels?.length) return null
  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <span className="tool-icon">🏨</span>
        <span className="tool-title">
          {data.city} 호텔 검색결과
        </span>
        <span className="tool-meta">
          {data.check_in} ~ {data.check_out} · {data.guests}명
        </span>
      </div>
      {onHotelClick && (
        <div className="hotel-click-hint">👆 호텔을 클릭하면 상세 정보를 볼 수 있습니다</div>
      )}
      <div className="hotel-grid">
        {data.hotels!.map((h, i) => (
          <HotelItem key={i} hotel={h} onHotelClick={onHotelClick} />
        ))}
      </div>
    </div>
  )
}

function HotelItem({ hotel, onHotelClick }: { hotel: Hotel; onHotelClick?: (hotelCode: string, hotelName: string) => void }) {
  const clickable = !!onHotelClick
  return (
    <div
      className={`hotel-item${clickable ? ' clickable-hotel' : ''}`}
      onClick={clickable ? () => onHotelClick(hotel.hotel_code, hotel.name) : undefined}
    >
      <div className="hotel-stars">{'★'.repeat(hotel.stars)}{'☆'.repeat(5 - hotel.stars)}</div>
      <div className="hotel-name">{hotel.name}</div>
      <div className="hotel-area">{hotel.area}</div>
      <div className="hotel-footer">
        <span className="hotel-rating">⭐ {hotel.rating}</span>
        <span className="hotel-price">{hotel.price.toLocaleString()}원<small>/박</small></span>
      </div>
      {clickable && <div className="hotel-detail-cta">상세 정보 보기 →</div>}
    </div>
  )
}

// ── 호텔 상세 카드 ─────────────────────────────
function HotelDetailCard({ data }: { data: HotelDetailResult }) {
  if (data.status !== 'success') return null
  return (
    <div className="tool-card hotel-detail-card">
      {/* 헤더 */}
      <div className="tool-card-header">
        <span className="tool-icon">🏨</span>
        <div className="hotel-detail-header-body">
          <span className="tool-title">{data.name}</span>
          <span className="hotel-detail-stars">{'★'.repeat(data.stars ?? 0)}{'☆'.repeat(5 - (data.stars ?? 0))}</span>
        </div>
        <span className="tool-meta">{data.city} · {data.area}</span>
      </div>

      {/* 평점 & 연락처 */}
      <div className="hotel-detail-meta-row">
        <span className="hotel-detail-rating">⭐ {data.rating} / 5.0</span>
        <span className="hotel-detail-address">📍 {data.address}</span>
        <span className="hotel-detail-phone">📞 {data.phone}</span>
      </div>

      {/* 설명 */}
      <div className="hotel-detail-description">{data.description}</div>

      {/* 하이라이트 */}
      {data.highlights && data.highlights.length > 0 && (
        <div className="hotel-detail-section">
          <div className="hotel-detail-section-title">✨ 주요 특징</div>
          <div className="hotel-highlights">
            {data.highlights.map((h, i) => (
              <span key={i} className="hotel-highlight-tag">{h}</span>
            ))}
          </div>
        </div>
      )}

      {/* 객실 타입 */}
      {data.room_types && data.room_types.length > 0 && (
        <div className="hotel-detail-section">
          <div className="hotel-detail-section-title">🛏️ 객실 타입</div>
          <div className="hotel-room-grid">
            {data.room_types.map((room, i) => (
              <RoomTypeItem key={i} room={room} />
            ))}
          </div>
        </div>
      )}

      {/* 편의시설 */}
      {data.amenities && data.amenities.length > 0 && (
        <div className="hotel-detail-section">
          <div className="hotel-detail-section-title">🎯 편의시설</div>
          <div className="hotel-amenities">
            {data.amenities.map((a, i) => (
              <span key={i} className="hotel-amenity-tag">{a}</span>
            ))}
          </div>
        </div>
      )}

      {/* 체크인/아웃 & 취소 정책 */}
      <div className="hotel-detail-policies">
        <div className="hotel-policy-item">
          <span className="hotel-policy-label">체크인</span>
          <span className="hotel-policy-value">{data.check_in_time}</span>
        </div>
        <div className="hotel-policy-divider" />
        <div className="hotel-policy-item">
          <span className="hotel-policy-label">체크아웃</span>
          <span className="hotel-policy-value">{data.check_out_time}</span>
        </div>
        <div className="hotel-policy-divider" />
        <div className="hotel-policy-item hotel-policy-cancel">
          <span className="hotel-policy-label">취소 정책</span>
          <span className="hotel-policy-value">{data.cancel_policy}</span>
        </div>
      </div>
    </div>
  )
}

function RoomTypeItem({ room }: { room: RoomType }) {
  return (
    <div className="hotel-room-item">
      <div className="hotel-room-type">{room.type}</div>
      <div className="hotel-room-meta">
        <span>{room.size}</span>
        <span>최대 {room.max_guests}명</span>
        <span>{room.bed}</span>
      </div>
      <div className="hotel-room-price">{room.price_per_night.toLocaleString()}원<small>/박</small></div>
    </div>
  )
}

// ── 항공 카드 ──────────────────────────────────
function FlightCard({ data }: { data: FlightSearchResult }) {
  if (data.status !== 'success') return null

  const isRoundTrip = data.trip_type === 'round_trip'
  const hasFlights = isRoundTrip
    ? (data.outbound_flights?.length || data.inbound_flights?.length)
    : data.flights?.length

  if (!hasFlights) return null

  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <span className="tool-icon">✈️</span>
        <span className="tool-title">
          {data.origin} ↔ {data.destination} {isRoundTrip ? '왕복' : '편도'}
        </span>
        <span className="tool-meta">
          {data.departure_date} {isRoundTrip && data.return_date && `~ ${data.return_date}`} · {data.passengers}명
        </span>
      </div>

      {isRoundTrip ? (
        <>
          {data.outbound_flights && data.outbound_flights.length > 0 && (
            <div className="flight-section">
              <div className="flight-section-title">출발편 ({data.origin} → {data.destination})</div>
              <div className="flight-list">
                {data.outbound_flights.map((f, i) => (
                  <FlightItem key={`out-${i}`} flight={f} />
                ))}
              </div>
            </div>
          )}

          {data.inbound_flights && data.inbound_flights.length > 0 && (
            <div className="flight-section">
              <div className="flight-section-title">귀국편 ({data.destination} → {data.origin})</div>
              <div className="flight-list">
                {data.inbound_flights.map((f, i) => (
                  <FlightItem key={`in-${i}`} flight={f} />
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="flight-list">
          {data.flights!.map((f, i) => (
            <FlightItem key={i} flight={f} />
          ))}
        </div>
      )}
    </div>
  )
}

function FlightItem({ flight }: { flight: Flight }) {
  return (
    <div className="flight-item">
      <div className="flight-airline">
        <span className="airline-name">{flight.airline}</span>
        <span className="flight-code">{flight.flight}</span>
        <span className="flight-class-badge">{flight.class}</span>
      </div>
      <div className="flight-route">
        <span className="flight-time">{flight.depart}</span>
        <span className="flight-arrow">
          <span className="flight-duration">{flight.duration}</span>
          <span className="flight-line">──────✈</span>
        </span>
        <span className="flight-time">{flight.arrive}</span>
      </div>
      <div className="flight-price">{flight.total_price.toLocaleString()}원</div>
    </div>
  )
}

// ── 여행 팁 카드 ──────────────────────────────
function TipsCard({ data }: { data: TravelTipsResult }) {
  if (data.status !== 'success') return null
  return (
    <div className="tool-card">
      <div className="tool-card-header">
        <span className="tool-icon">🗺️</span>
        <span className="tool-title">{data.destination} 여행 정보</span>
        <span className="tool-meta">{data.best_season}</span>
      </div>
      <p className="tips-overview">{data.overview}</p>
      <div className="tips-grid">
        {data.spots?.length && (
          <div className="tips-section">
            <div className="tips-section-title">📍 주요 관광지</div>
            <ul>{data.spots.map((s, i) => <li key={i}>{s}</li>)}</ul>
          </div>
        )}
        {data.food?.length && (
          <div className="tips-section">
            <div className="tips-section-title">🍜 추천 음식</div>
            <ul>{data.food.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
        )}
        {data.tips?.length && (
          <div className="tips-section">
            <div className="tips-section-title">💡 여행 팁</div>
            <ul>{data.tips.map((t, i) => <li key={i}>{t}</li>)}</ul>
          </div>
        )}
      </div>
      <div className="tips-meta-row">
        <span>💱 {data.currency}</span>
        <span>🗣️ {data.language}</span>
      </div>
    </div>
  )
}
