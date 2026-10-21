from django.contrib.auth.models import User
from django.contrib.auth.password_validation import (
    validate_password,
)
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.db import transaction

from rest_framework import serializers
from rest_framework.authtoken.models import Token

from .models import PerfilUsuario
from .serializers import StrictSerializer


def _normalizar_email(email):
    return str(email).strip().lower()


def _validar_password_django(
    password,
    usuario,
):
    try:
        validate_password(
            password,
            user=usuario,
        )

    except DjangoValidationError as error:
        raise serializers.ValidationError(
            list(error.messages)
        ) from error


def _configurar_perfil(
    perfil,
    rol,
):
    perfil.rol = rol
    perfil.autorizado = True

    perfil.puede_gestionar_datos = (
        rol
        in {
            PerfilUsuario.Rol.ENCARGADO,
            PerfilUsuario.Rol.ADMINISTRADOR,
        }
    )

    perfil.save(
        update_fields=[
            "rol",
            "autorizado",
            "puede_gestionar_datos",
        ]
    )


class CrearUsuarioSerializer(
    StrictSerializer
):
    username = serializers.CharField(
        min_length=3,
        max_length=150,
        trim_whitespace=True,
    )

    first_name = serializers.CharField(
        min_length=1,
        max_length=150,
        trim_whitespace=True,
    )

    last_name = serializers.CharField(
        min_length=1,
        max_length=150,
        trim_whitespace=True,
    )

    email = serializers.EmailField(
        max_length=254,
    )

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    rol = serializers.ChoiceField(
        choices=
            PerfilUsuario.Rol.choices,
    )

    activo = serializers.BooleanField(
        required=False,
        default=True,
    )

    def validate_username(
        self,
        value,
    ):
        username = value.strip()

        campo_username = (
            User._meta.get_field(
                "username"
            )
        )

        try:
            campo_username.run_validators(
                username
            )

        except DjangoValidationError as error:
            raise serializers.ValidationError(
                list(error.messages)
            ) from error

        if (
            User.objects
            .filter(
                username__iexact=username
            )
            .exists()
        ):
            raise serializers.ValidationError(
                (
                    "Ya existe un usuario "
                    "con este nombre."
                )
            )

        return username

    def validate_email(
        self,
        value,
    ):
        email = _normalizar_email(
            value
        )

        if (
            User.objects
            .filter(
                email__iexact=email
            )
            .exists()
        ):
            raise serializers.ValidationError(
                (
                    "Ya existe un usuario "
                    "con este correo electrónico."
                )
            )

        return email

    def validate(
        self,
        attrs,
    ):
        attrs = super().validate(
            attrs
        )

        password = attrs.get(
            "password"
        )

        confirmacion = attrs.get(
            "password_confirm"
        )

        if password != confirmacion:
            raise serializers.ValidationError(
                {
                    "password_confirm": [
                        (
                            "Las contraseñas "
                            "no coinciden."
                        )
                    ]
                }
            )

        usuario_temporal = User(
            username=
                attrs.get(
                    "username",
                    "",
                ),

            first_name=
                attrs.get(
                    "first_name",
                    "",
                ),

            last_name=
                attrs.get(
                    "last_name",
                    "",
                ),

            email=
                attrs.get(
                    "email",
                    "",
                ),
        )

        _validar_password_django(
            password,
            usuario_temporal,
        )

        return attrs

    @transaction.atomic
    def create(
        self,
        validated_data,
    ):
        validated_data.pop(
            "password_confirm"
        )

        rol = validated_data.pop(
            "rol"
        )

        activo = validated_data.pop(
            "activo",
            True,
        )

        password = validated_data.pop(
            "password"
        )

        usuario = (
            User.objects.create_user(
                password=password,
                is_active=activo,
                **validated_data,
            )
        )

        _configurar_perfil(
            usuario.perfil_cintac,
            rol,
        )

        return usuario


class ActualizarUsuarioSerializer(
    StrictSerializer
):
    first_name = serializers.CharField(
        min_length=1,
        max_length=150,
        trim_whitespace=True,
        required=False,
    )

    last_name = serializers.CharField(
        min_length=1,
        max_length=150,
        trim_whitespace=True,
        required=False,
    )

    email = serializers.EmailField(
        max_length=254,
        required=False,
    )

    rol = serializers.ChoiceField(
        choices=
            PerfilUsuario.Rol.choices,
        required=False,
    )

    activo = serializers.BooleanField(
        required=False,
    )

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        required=False,
        allow_blank=False,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        required=False,
        allow_blank=False,
    )

    def validate_email(
        self,
        value,
    ):
        email = _normalizar_email(
            value
        )

        consulta = (
            User.objects
            .filter(
                email__iexact=email
            )
            .exclude(
                id=self.instance.id
            )
        )

        if consulta.exists():
            raise serializers.ValidationError(
                (
                    "Ya existe un usuario "
                    "con este correo electrónico."
                )
            )

        return email

    def validate(
        self,
        attrs,
    ):
        attrs = super().validate(
            attrs
        )

        password = attrs.get(
            "password"
        )

        confirmacion = attrs.get(
            "password_confirm"
        )

        if (
            password is not None
            or confirmacion is not None
        ):
            if (
                not password
                or not confirmacion
            ):
                raise serializers.ValidationError(
                    {
                        "password_confirm": [
                            (
                                "Debe ingresar y "
                                "confirmar la nueva "
                                "contraseña."
                            )
                        ]
                    }
                )

            if password != confirmacion:
                raise serializers.ValidationError(
                    {
                        "password_confirm": [
                            (
                                "Las contraseñas "
                                "no coinciden."
                            )
                        ]
                    }
                )

            _validar_password_django(
                password,
                self.instance,
            )

        request = self.context.get(
            "request"
        )

        usuario_actual = (
            request.user
            if request
            else None
        )

        nuevo_rol = attrs.get(
            "rol",
            self.instance
            .perfil_cintac
            .rol,
        )

        nuevo_activo = attrs.get(
            "activo",
            self.instance.is_active,
        )

        if (
            usuario_actual
            and
            usuario_actual.id
            == self.instance.id
        ):
            if not nuevo_activo:
                raise serializers.ValidationError(
                    {
                        "activo": [
                            (
                                "No puede desactivar "
                                "su propia cuenta."
                            )
                        ]
                    }
                )

            if (
                not usuario_actual.is_superuser
                and
                nuevo_rol
                != PerfilUsuario
                .Rol
                .ADMINISTRADOR
            ):
                raise serializers.ValidationError(
                    {
                        "rol": [
                            (
                                "No puede quitarse "
                                "a sí mismo el rol "
                                "de administrador."
                            )
                        ]
                    }
                )

        perfil_actual = (
            self.instance
            .perfil_cintac
        )

        pierde_administracion = (
            perfil_actual.rol
            == PerfilUsuario
            .Rol
            .ADMINISTRADOR
            and
            (
                nuevo_rol
                != PerfilUsuario
                .Rol
                .ADMINISTRADOR
                or
                not nuevo_activo
            )
        )

        if pierde_administracion:
            otros_admin = (
                PerfilUsuario.objects
                .filter(
                    rol=
                        PerfilUsuario
                        .Rol
                        .ADMINISTRADOR,

                    autorizado=True,

                    usuario__is_active=True,
                )
                .exclude(
                    usuario_id=
                        self.instance.id
                )
                .exists()
            )

            if not otros_admin:
                raise serializers.ValidationError(
                    {
                        "rol": [
                            (
                                "Debe existir al menos "
                                "un administrador activo."
                            )
                        ]
                    }
                )

        return attrs

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):
        validated_data.pop(
            "password_confirm",
            None,
        )

        password = validated_data.pop(
            "password",
            None,
        )

        rol = validated_data.pop(
            "rol",
            instance
            .perfil_cintac
            .rol,
        )

        activo = validated_data.pop(
            "activo",
            instance.is_active,
        )

        for campo, valor in (
            validated_data.items()
        ):
            setattr(
                instance,
                campo,
                valor,
            )

        instance.is_active = activo

        if password:
            instance.set_password(
                password
            )

        instance.save()

        _configurar_perfil(
            instance.perfil_cintac,
            rol,
        )

        if not activo:
            Token.objects.filter(
                user=instance
            ).delete()

        return instance