import { afterEach, describe, expect, it } from 'vitest'
import { i18n } from './index'

afterEach(() => {
  i18n.global.locale.value = 'id'
})

describe('approved Indonesian dashboard copy', () => {
  it('renders the approved copy across all seven sections', () => {
    i18n.global.locale.value = 'id'
    const expected = {
      'home.studio': 'Workstation Video Pendek AI',
      'home.description': 'Gabungkan Inspirasi, storyboard dan hasil ke dalam satu kanvas, biarkan setiap klip bersatu',
      'home.create': 'Membuat Workspace',
      'home.continue': 'Lanjutkan Proyek',
      'common.workspaces': 'Workspace',
      'workspace.library': 'Gudang Proyek',
      'workspace.title': 'PROYEK',
      'workspace.newDescription': 'Buat kanvas baru',
      'workspace.sort': 'filter',
      'navigation.overview': 'informasi akun',
      'navigation.recharge': 'Top-up Kredit',
      'navigation.generations': 'Riwayat Proyek',
      'navigation.credits': 'Riwayat Top-Up Kredit',
      'navigation.pricing': 'Daftar Harga',
      'account.available': 'kuota kredit',
      'account.profileDescription': 'Informasi akun hanya untuk dilihat',
      'account.registered': 'Tanggal',
      'account.invite': 'referal',
      'recharge.title': 'Top-up Kredit',
      'recharge.selectProvider': 'Pilih Metode Pembayaran',
      'recharge.providerFixedAfterOrder': 'Metode Pembayaran, Mata Uang dan Kredit akan ditetapkan setelah pembayaran',
      'recharge.payment': 'Riwayat Pesanan',
      'recharge.selectAmount': 'Pilih Nominal Top-Up',
      'recharge.baseTier': 'Paket Dasar',
      'recharge.customAmount': 'Nominal Lainnya',
      'records.history': 'Riwayat Proyek',
      'records.allMedia': 'Jenis Proyek',
      'records.allStatuses': 'Status',
      'records.historyEmpty': 'Belum terdapat Riwayat Proyek',
      'records.historyFilterEmpty': 'Tidak terdapat tugas apapun di filter',
      'records.ledger': 'Riwayat Top-Up Kredit',
      'records.allTypes': 'Riwayat Kredit',
      'records.thirtyDays': 'Waktu',
      'records.ledgerEmpty': 'Belum terdapat riwayat top-up kredit',
      'records.pricing': 'Daftar Harga',
      'records.pricingSubtitle': 'Proyek generasi berdasarkan daftar harga berikut',
      'records.mediaType': 'Jenis Proyek',
      'records.model': 'Jenis Model',
      'records.billingUnit': 'Metode Perhitungan',
      'records.creditRate': 'Biaya Kredit',
    }
    for (const [key, value] of Object.entries(expected)) {
      expect(i18n.global.t(key), key).toBe(value)
    }
    expect(`${i18n.global.t('home.headline')} ${i18n.global.t('home.workspace')}`)
      .toBe('Workstation Video Pendek E-Commerce Berbasis AI')
  })

  it('preserves recharge amount interpolation', () => {
    i18n.global.locale.value = 'id'
    expect(i18n.global.t('recharge.amountRange', { min: 'Rp 150.000', max: 'Rp 15.000.000' }))
      .toBe('Nilai Top-Up per transaksi Rp 150.000 - Rp 15.000.000')
  })
})
