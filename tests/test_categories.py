import models


# --- Seeding tests ---

def test_short_video_category_seeded(db, client):
    cats = [c.name for c in db.query(models.Category).all()]
    assert "Short Video" in cats


def test_subcategory_groups_seeded(db, client):
    groups = {g.name: [o.name for o in g.options]
              for g in db.query(models.SubcategoryGroup).all()}
    assert "Copyright Status" in groups
    assert "Use Purpose" in groups
    assert "Copyrighted" in groups["Copyright Status"]
    assert "Not Copyrighted" in groups["Copyright Status"]
    assert "Personal" in groups["Use Purpose"]
    assert "Commercial" in groups["Use Purpose"]


# --- Admin-only category route tests ---

def test_guest_cannot_add_category(guest_client):
    r = guest_client.post("/add-category", data={"name": "TestCat"}, follow_redirects=False)
    assert r.status_code == 403


def test_admin_can_add_category(admin_client, db):
    admin_client.post("/add-category", data={"name": "MyNewCat"}, follow_redirects=False)
    assert db.query(models.Category).filter_by(name="MyNewCat").first() is not None


def test_guest_cannot_delete_category(guest_client, db):
    cat = db.query(models.Category).filter_by(name="Photography").first()
    r = guest_client.post(f"/delete-category/{cat.id}", follow_redirects=False)
    assert r.status_code == 403


# --- Subcategory option route tests ---

def test_guest_cannot_add_subcategory_option(guest_client, db):
    group = db.query(models.SubcategoryGroup).filter_by(name="Copyright Status").first()
    r = guest_client.post(
        "/add-subcategory-option",
        data={"group_id": group.id, "option_name": "Unknown"},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_admin_can_add_subcategory_option(admin_client, db):
    group = db.query(models.SubcategoryGroup).filter_by(name="Use Purpose").first()
    admin_client.post(
        "/add-subcategory-option",
        data={"group_id": group.id, "option_name": "Educational"},
        follow_redirects=False,
    )
    db.expire_all()
    opt = db.query(models.SubcategoryOption).filter_by(
        name="Educational", group_id=group.id
    ).first()
    assert opt is not None


def test_admin_can_delete_subcategory_option(admin_client, db):
    opt = db.query(models.SubcategoryOption).filter_by(name="Personal").first()
    assert opt is not None
    admin_client.post(f"/delete-subcategory-option/{opt.id}", follow_redirects=False)
    db.expire_all()
    assert db.query(models.SubcategoryOption).filter_by(id=opt.id).first() is None


# --- Edit asset subcategory tests ---

def _make_asset(db):
    cat = db.query(models.Category).filter_by(name="Photography").first()
    asset = models.DBMediaAsset(
        name="Test Asset",
        file_path="test.jpg",
        ai_tags="test",
        category_id=cat.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def test_edit_updates_subcategory_ids(admin_client, db):
    asset = _make_asset(db)
    copy_opt = db.query(models.SubcategoryOption).filter_by(name="Copyrighted").first()
    purp_opt = db.query(models.SubcategoryOption).filter_by(name="Commercial").first()
    cat = db.query(models.Category).filter_by(name="Photography").first()

    admin_client.post(
        f"/edit/{asset.id}",
        data={
            "name": asset.name,
            "ai_tags": asset.ai_tags,
            "category_id": cat.id,
            "copyright_option_id": copy_opt.id,
            "use_purpose_option_id": purp_opt.id,
        },
        follow_redirects=False,
    )
    db.expire_all()
    updated = db.query(models.DBMediaAsset).filter_by(id=asset.id).first()
    assert updated.copyright_option_id == copy_opt.id
    assert updated.use_purpose_option_id == purp_opt.id


def test_edit_clears_subcategory_when_empty(admin_client, db):
    asset = _make_asset(db)
    cat = db.query(models.Category).filter_by(name="Photography").first()

    admin_client.post(
        f"/edit/{asset.id}",
        data={
            "name": asset.name,
            "ai_tags": asset.ai_tags,
            "category_id": cat.id,
        },
        follow_redirects=False,
    )
    db.expire_all()
    updated = db.query(models.DBMediaAsset).filter_by(id=asset.id).first()
    assert updated.copyright_option_id is None
    assert updated.use_purpose_option_id is None
